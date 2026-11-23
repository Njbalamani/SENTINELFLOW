from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ROLE_VIEWER, User
from apps.detection.models import DetectionResult
from apps.monitoring.models import ActivitySource, ActivityType, UserActivity
from apps.monitoring.services import is_off_hours, record_activity


class MonitoringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="actor", password="Pass!2026", role=ROLE_VIEWER)

    def test_record_activity_runs_detection_pipeline(self):
        activity = record_activity(
            self.user, ActivityType.FAILED_LOGIN, resource="/private/payroll.csv",
            action_detail="repeated failures", source=ActivitySource.SYNTHETIC,
        )
        self.assertTrue(UserActivity.objects.filter(pk=activity.pk).exists())
        self.assertTrue(DetectionResult.objects.filter(activity=activity).exists())

    def test_off_hours_flag_is_derived_from_timestamp(self):
        self.assertTrue(is_off_hours(timezone.now().replace(hour=2, minute=0)))
        self.assertFalse(is_off_hours(timezone.now().replace(hour=12, minute=0)))

    def test_bulk_history_is_used_for_feature_engineering(self):
        now = timezone.now()
        for index in range(6):
            UserActivity.objects.create(
                user=self.user, activity_type=ActivityType.DOWNLOAD, timestamp=now - timedelta(minutes=index),
                bytes_transferred=50_000_000, resource=f"/file-{index}.csv",
            )
        activity = record_activity(self.user, ActivityType.DOWNLOAD)
        detection = DetectionResult.objects.get(activity=activity)
        self.assertGreaterEqual(detection.features["download_count_1h"], 6)
        self.assertGreater(detection.features["log_bytes_1h"], 0)

    def test_activity_list_scopes_viewer_to_own_events(self):
        other = User.objects.create_user(username="other", password="Pass!2026")
        UserActivity.objects.create(user=other, activity_type=ActivityType.LOGIN, timestamp=timezone.now())
        own = UserActivity.objects.create(user=self.user, activity_type=ActivityType.LOGIN, timestamp=timezone.now())
        self.client.force_login(self.user)
        response = self.client.get("/monitoring/")
        self.assertEqual(response.status_code, 200)
        ids = [item.pk for item in response.context["activities"]]
        self.assertEqual(ids, [own.pk])
