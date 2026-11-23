from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ROLE_ANALYST, ROLE_VIEWER, User
from apps.alerts.models import AlertStatus, SecurityAlert, Severity
from apps.alerts.services import change_status, create_alert_from_detection
from apps.detection.models import Classification, DetectionResult
from apps.monitoring.models import ActivityType, UserActivity


class AlertTests(TestCase):
    def setUp(self):
        self.analyst = User.objects.create_user(username="analyst", password="Pass!2026", role=ROLE_ANALYST)
        self.viewer = User.objects.create_user(username="viewer", password="Pass!2026", role=ROLE_VIEWER)
        self.activity = UserActivity.objects.create(
            user=self.viewer, activity_type=ActivityType.DOWNLOAD, timestamp=timezone.now()
        )
        self.detection = DetectionResult.objects.create(
            activity=self.activity, user=self.viewer, classification=Classification.CRITICAL,
            risk_score=92, reasons=["Large outbound transfer"],
        )

    def test_alert_is_created_with_correct_severity_and_evidence(self):
        alert = create_alert_from_detection(self.detection)
        self.assertEqual(alert.severity, Severity.CRITICAL)
        self.assertEqual(alert.status, AlertStatus.OPEN)
        self.assertIn("Large outbound transfer", str(alert.evidence))

    def test_duplicate_detections_are_deduplicated(self):
        first = create_alert_from_detection(self.detection)
        second = create_alert_from_detection(self.detection)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.notes.count(), 1)

    def test_status_change_sets_resolution_timestamp_and_actor(self):
        alert = create_alert_from_detection(self.detection)
        change_status(alert, AlertStatus.RESOLVED, actor=self.analyst, notes="Confirmed authorized export")
        alert.refresh_from_db()
        self.assertEqual(alert.assigned_to, self.analyst)
        self.assertIsNotNone(alert.resolved_at)
        self.assertIn("authorized", alert.resolution_notes)

    def test_alert_detail_post_requires_security_role(self):
        alert = create_alert_from_detection(self.detection)
        self.client.force_login(self.viewer)
        response = self.client.post(
            f"/alerts/{alert.pk}/", {"action": "update", "status": "RESOLVED", "resolution_notes": "x"}
        )
        self.assertEqual(response.status_code, 403)
        alert.refresh_from_db()
        self.assertEqual(alert.status, AlertStatus.OPEN)
