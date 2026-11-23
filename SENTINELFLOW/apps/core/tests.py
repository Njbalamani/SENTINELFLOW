from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, User
from apps.alerts.models import SecurityAlert, Severity
from apps.core.models import AuditLog
from apps.monitoring.models import ActivitySource, ActivityType, UserActivity


class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin", password="Pass!2026", role=ROLE_ADMIN, is_staff=True, is_superuser=True
        )
        self.analyst = User.objects.create_user(username="analyst", password="Pass!2026", role=ROLE_ANALYST)
        self.viewer = User.objects.create_user(username="viewer", password="Pass!2026", role=ROLE_VIEWER)

    def test_authentication_is_required(self):
        self.assertEqual(self.client.get("/api/v1/activities/").status_code, 403)

    def test_viewer_has_read_only_api_access(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get("/api/v1/activities/").status_code, 200)
        response = self.client.post("/api/v1/activities/", {
            "user": self.viewer.pk, "activity_type": "LOGIN", "timestamp": "2026-11-23T10:00:00Z",
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_ingest_api_analyses_activity(self):
        self.client.force_authenticate(self.analyst)
        response = self.client.post("/api/v1/activities/", {
            "user": self.viewer.pk, "activity_type": "DOWNLOAD", "timestamp": "2026-11-23T10:00:00Z",
            "bytes_transferred": 1000, "source": "API",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        activity = UserActivity.objects.get(pk=response.data["id"])
        self.assertEqual(activity.source, ActivitySource.API)
        self.assertIsNotNone(response.data["classification"])

    def test_reject_negative_bytes(self):
        self.client.force_authenticate(self.analyst)
        response = self.client.post("/api/v1/activities/", {
            "user": self.viewer.pk, "activity_type": "DOWNLOAD", "timestamp": "2026-11-23T10:00:00Z",
            "bytes_transferred": -5,
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_alert_status_action_and_audit_logging(self):
        alert = SecurityAlert.objects.create(
            title="test", description="test", severity=Severity.HIGH, user=self.viewer
        )
        self.client.force_authenticate(self.analyst)
        response = self.client.post(f"/api/v1/alerts/{alert.pk}/status/", {"status": "INVESTIGATING"}, format="json")
        self.assertEqual(response.status_code, 200)
        alert.refresh_from_db()
        self.assertEqual(alert.status, "INVESTIGATING")
        self.assertTrue(AuditLog.objects.filter(action="STATUS_CHANGE", entity_id=str(alert.pk)).exists())

    def test_analytics_summary_is_live_and_analyst_only(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get("/api/v1/analytics/summary/").status_code, 403)
        UserActivity.objects.create(user=self.viewer, activity_type=ActivityType.LOGIN, timestamp="2026-11-23T10:00:00Z")
        self.client.force_authenticate(self.analyst)
        response = self.client.get("/api/v1/analytics/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stats"]["total_activities"], 1)

    def test_health_endpoint(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_token_endpoint_returns_token(self):
        User.objects.create_user(username="tokenuser", password="Pass!2026", role=ROLE_ANALYST)
        response = self.client.post("/api/v1/auth/token/", {
            "username": "tokenuser", "password": "Pass!2026",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
