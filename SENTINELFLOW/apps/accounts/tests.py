from django.test import TestCase
from django.urls import reverse

from apps.accounts.forms import UserRegistrationForm
from apps.accounts.models import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, User
from apps.core.models import AuditLog
from apps.monitoring.models import ActivityType, UserActivity


class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = "TestPass!2026"
        self.admin = User.objects.create_user(
            username="admin", password=self.password, role=ROLE_ADMIN, is_staff=True, is_superuser=True
        )
        self.viewer = User.objects.create_user(username="viewer", password=self.password, role=ROLE_VIEWER)

    def test_login_records_activity_and_audit(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "viewer", "password": self.password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            UserActivity.objects.filter(user=self.viewer, activity_type=ActivityType.LOGIN).count(), 1
        )
        self.assertTrue(AuditLog.objects.filter(actor=self.viewer, action="LOGIN").exists())

    def test_failed_login_is_audited(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "viewer", "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="DENIED").exists())

    def test_logout_requires_post_and_records_event(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertTrue(
            UserActivity.objects.filter(user=self.viewer, activity_type=ActivityType.LOGOUT).exists()
        )

    def test_registration_form_rejects_duplicate_email(self):
        User.objects.create_user(username="existing", email="taken@example.com", password=self.password)
        form = UserRegistrationForm(data={
            "username": "newuser", "email": "TAKEN@example.com", "role": ROLE_ANALYST,
            "password1": "Another!Pass2026", "password2": "Another!Pass2026",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_viewer_cannot_access_admin_pages(self):
        self.client.force_login(self.viewer)
        for name in ("accounts:users", "core:audit", "detection:models"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 403, name)

    def test_analyst_can_open_dashboard_but_not_admin_pages(self):
        analyst = User.objects.create_user(username="analyst", password=self.password, role=ROLE_ANALYST)
        self.client.force_login(analyst)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("accounts:users")).status_code, 403)
