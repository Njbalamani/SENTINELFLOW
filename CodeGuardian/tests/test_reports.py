import json
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.reports.pdf import create_pdf_report
from apps.reports.services import create_json_report, json_download_response, scan_payload
from apps.scan.models import Scan
from apps.scan.services import process_upload, run_scan
from tests.test_analysis import TEST_CONFIG
from tests.test_scans import VULNERABLE_PY

MEDIA_ROOT = tempfile.mkdtemp(prefix="codeguardian-report-tests-")


@override_settings(MEDIA_ROOT=MEDIA_ROOT, CODEGUARDIAN=TEST_CONFIG)
class ReportTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reporter", password="StrongPass@2026"
        )
        self.scan = Scan(owner=self.user, name="Report scan", original_filename="vulnerable.py")
        upload = SimpleUploadedFile("vulnerable.py", VULNERABLE_PY.encode(), content_type="text/x-python")
        process_upload(self.scan, upload)
        run_scan(self.scan)

    def test_payload_contains_scan_metadata_and_findings(self):
        payload = scan_payload(self.scan)
        self.assertEqual(payload["platform"], "CODEGUARDIAN")
        self.assertEqual(payload["scan"]["id"], str(self.scan.id))
        self.assertGreaterEqual(len(payload["findings"]), 2)
        self.assertIn("CRITICAL", payload["severity_counts"])

    def test_pdf_report_is_written_and_registered(self):
        report = create_pdf_report(self.scan, self.user)
        self.assertEqual(report.format, "PDF")
        self.assertTrue(Path(report.file.path).exists())
        self.client.force_login(self.user)
        response = self.client.get(reverse("reports:download", args=[report.pk]))
        self.assertEqual(response.status_code, 200)

    def test_json_report_and_download_response(self):
        report = create_json_report(self.scan, self.user)
        self.assertEqual(report.format, "JSON")
        data = json.loads(Path(report.file.path).read_text(encoding="utf-8"))
        self.assertEqual(data["scan"]["id"], str(self.scan.id))
        response = json_download_response(self.scan)
        self.assertEqual(response["Content-Type"], "application/json; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])
