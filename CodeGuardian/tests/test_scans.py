import shutil
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.scan.models import Finding, Scan
from apps.scan.services import process_upload, run_scan
from tests.test_analysis import TEST_CONFIG

MEDIA_ROOT = tempfile.mkdtemp(prefix="codeguardian-tests-")
VULNERABLE_PY = (
    'API_KEY = "AKIA1234567890ABCDEF"\n'
    'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n'
    'token = "supersecrettoken"\n'
)


@override_settings(MEDIA_ROOT=MEDIA_ROOT, CODEGUARDIAN=TEST_CONFIG)
class ScanWorkflowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="analyst", password="StrongPass@2026", plan="DEVELOPER"
        )
        self.client.force_login(self.user)

    def test_upload_view_creates_completed_scan_with_findings(self):
        upload = SimpleUploadedFile("vulnerable.py", VULNERABLE_PY.encode(), content_type="text/x-python")
        response = self.client.post(
            reverse("scan:upload"), {"name": "Demo scan", "source_file": upload}
        )
        self.assertEqual(response.status_code, 302)
        scan = Scan.objects.get(owner=self.user)
        self.assertEqual(scan.status, Scan.Status.COMPLETED)
        self.assertEqual(scan.files_scanned, 1)
        self.assertGreaterEqual(scan.total_vulnerabilities, 2)
        self.assertTrue(Finding.objects.filter(scan=scan).exists())
        self.assertLess(scan.security_score, 100)

    def test_scan_result_view_is_owner_scoped(self):
        scan = Scan.objects.create(owner=self.user, name="Private scan", original_filename="a.py")
        other = get_user_model().objects.create_user(username="other", password="StrongPass@2026")
        self.client.force_login(other)
        response = self.client.get(reverse("scan:result", args=[scan.pk]))
        self.assertEqual(response.status_code, 403)

    def test_zip_path_traversal_is_rejected(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../evil.py", "print('escape')")
        upload = SimpleUploadedFile("project.zip", buffer.getvalue(), content_type="application/zip")
        scan = Scan(owner=self.user, name="Unsafe ZIP", original_filename="project.zip")
        with self.assertRaises(SuspiciousOperation):
            process_upload(scan, upload)

    def test_scan_helper_can_run_from_unsaved_model(self):
        upload = SimpleUploadedFile("clean.js", b"const name = 'safe';", content_type="text/javascript")
        scan = Scan(owner=self.user, name="Clean scan", original_filename="clean.js")
        process_upload(scan, upload)
        run_scan(scan)
        scan.refresh_from_db()
        self.assertEqual(scan.status, Scan.Status.COMPLETED)
        self.assertEqual(scan.total_vulnerabilities, 0)
        self.assertEqual(scan.security_score, 100)
        self.assertTrue(Path(scan.files.first().file.path).exists())
