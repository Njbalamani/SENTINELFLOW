from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ROLE_ANALYST, User
from apps.alerts.models import SecurityAlert, Severity
from apps.analytics.services import dashboard_stats, daily_activity, risk_distribution
from apps.detection.models import Classification, DetectionResult, UserRiskProfile
from apps.monitoring.models import ActivityType, UserActivity


class AnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="Pass!2026", role=ROLE_ANALYST)

    def test_dashboard_stats_derive_from_database(self):
        empty = dashboard_stats()
        self.assertEqual(empty["total_activities"], 0)
        for index in range(4):
            activity = UserActivity.objects.create(
                user=self.user, activity_type=ActivityType.DOWNLOAD, timestamp=timezone.now()
            )
            DetectionResult.objects.create(
                activity=activity, user=self.user,
                classification=Classification.CRITICAL, risk_score=90,
            )
        SecurityAlert.objects.create(
            title="Critical", description="x", severity=Severity.CRITICAL, user=self.user
        )
        populated = dashboard_stats()
        self.assertEqual(populated["total_activities"], 4)
        self.assertEqual(populated["critical_activities"], 4)
        self.assertEqual(populated["critical_alerts"], 1)
        self.assertEqual(populated["monitored_users"], 1)

    def test_daily_activity_returns_equal_length_series(self):
        data = daily_activity(7)
        self.assertEqual(len(data["labels"]), 7)
        self.assertEqual(len(data["activities"]), 7)
        self.assertEqual(len(data["detections"]), 7)

    def test_risk_distribution_includes_all_levels(self):
        UserRiskProfile.objects.create(user=self.user, risk_score=10, risk_level="LOW")
        self.assertEqual(len(risk_distribution()), 4)

    def test_dashboard_view_embeds_live_chart_data(self):
        self.client.force_login(self.user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "chart-data")
        self.assertIn("stats", response.context)
