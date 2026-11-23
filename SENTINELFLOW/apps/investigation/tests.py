from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ROLE_ANALYST, User
from apps.alerts.models import AlertStatus, SecurityAlert, Severity
from apps.detection.models import Classification, DetectionResult
from apps.investigation.models import CaseStatus, InvestigationCase
from apps.investigation.services import add_note, close_case, create_case_from_alert
from apps.monitoring.models import ActivityType, UserActivity


class InvestigationTests(TestCase):
    def setUp(self):
        self.analyst = User.objects.create_user(username="analyst", password="Pass!2026", role=ROLE_ANALYST)
        self.subject = User.objects.create_user(username="subject", password="Pass!2026")
        activity = UserActivity.objects.create(
            user=self.subject, activity_type=ActivityType.FILE_ACCESS, timestamp=timezone.now()
        )
        detection = DetectionResult.objects.create(
            activity=activity, user=self.subject, classification=Classification.SUSPICIOUS, risk_score=70
        )
        self.alert = SecurityAlert.objects.create(
            title="Suspicious access", description="Abnormal file access volume", severity=Severity.HIGH,
            user=self.subject, activity=activity, detection=detection,
        )

    def test_case_created_from_alert_is_idempotent(self):
        first, created = create_case_from_alert(self.alert, actor=self.analyst)
        second, created_again = create_case_from_alert(self.alert, actor=self.analyst)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.subject, self.subject)

    def test_add_note_moves_open_case_to_in_progress(self):
        case, _ = create_case_from_alert(self.alert, actor=self.analyst)
        add_note(case, self.analyst, "Reviewed proxy logs")
        case.refresh_from_db()
        self.assertEqual(case.status, CaseStatus.IN_PROGRESS)
        self.assertEqual(case.case_notes.count(), 1)

    def test_close_case_resolves_linked_alert(self):
        case, _ = create_case_from_alert(self.alert, actor=self.analyst)
        close_case(case, actor=self.analyst, conclusion="Authorized migration")
        case.refresh_from_db()
        self.alert.refresh_from_db()
        self.assertEqual(case.status, CaseStatus.CLOSED)
        self.assertEqual(self.alert.status, AlertStatus.RESOLVED)
