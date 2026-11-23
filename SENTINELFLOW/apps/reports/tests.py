from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ROLE_ANALYST, User
from apps.alerts.models import SecurityAlert, Severity
from apps.investigation.models import InvestigationCase
from apps.reports.models import GeneratedReport
from apps.reports.services import generate_report


class ReportTests(TestCase):
    def setUp(self):
        self.analyst = User.objects.create_user(username="analyst", password="Pass!2026", role=ROLE_ANALYST)
        self.subject = User.objects.create_user(username="subject", password="Pass!2026")
        self.alert = SecurityAlert.objects.create(
            title="Critical exfiltration", description="Mass download detected",
            severity=Severity.CRITICAL, user=self.subject,
        )
        self.case = InvestigationCase.objects.create(title="Case", subject=self.subject)

    def test_pdf_builders_produce_valid_pdf_header(self):
        cases = [
            (GeneratedReport.ReportType.ALERT, {"alert": self.alert}),
            (GeneratedReport.ReportType.RISK, {}),
            (GeneratedReport.ReportType.ACTIVITY, {"user": self.subject}),
            (GeneratedReport.ReportType.INVESTIGATION, {"case": self.case}),
        ]
        for kind, kwargs in cases:
            with self.subTest(kind=kind):
                report = generate_report(kind, generated_by=self.analyst, **kwargs)
                self.assertTrue(report.file.name.endswith(".pdf"))
                with report.file.open("rb") as handle:
                    self.assertEqual(handle.read(4), b"%PDF")

    def test_report_requires_related_object(self):
        with self.assertRaises(ValueError):
            generate_report(GeneratedReport.ReportType.ALERT, generated_by=self.analyst)

    def test_download_endpoint_streams_pdf(self):
        report = generate_report(GeneratedReport.ReportType.RISK, generated_by=self.analyst)
        self.client.force_login(self.analyst)
        response = self.client.get(f"/reports/download/{report.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
