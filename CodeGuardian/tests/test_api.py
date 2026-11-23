import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.scan.models import Scan, ScanFile
from apps.scan.services import process_upload, run_scan
from tests.test_analysis import TEST_CONFIG
from tests.test_scans import VULNERABLE_PY

MEDIA_ROOT = tempfile.mkdtemp(prefix="codeguardian-api-tests-")


@override_settings(MEDIA_ROOT=MEDIA_ROOT, CODEGUARDIAN=TEST_CONFIG)
class ApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="apiuser", password="StrongPass@2026"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()

    def test_token_endpoint_returns_token(self):
        response = self.client.post(
            reverse("api:token"), {"username": "apiuser", "password": "StrongPass@2026"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)

    def test_authenticated_list_and_summary(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        scan = Scan.objects.create(
            owner=self.user,
            name="API scan",
            status=Scan.Status.COMPLETED,
            original_filename="x.py",
            security_score=90,
        )
        list_response = self.client.get(reverse("api:scan-list"))
        summary_response = self.client.get(reverse("api:analytics-summary"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.data["total_scans"], 1)
        self.assertTrue(any(item["id"] == str(scan.id) for item in list_response.data["results"]))

    def test_api_create_scan_upload(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        upload = SimpleUploadedFile("api_vuln.py", VULNERABLE_PY.encode(), content_type="text/x-python")
        response = self.client.post(
            reverse("api:scan-list"),
            {"name": "API upload", "source_file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Scan.Status.COMPLETED)
        self.assertGreaterEqual(response.data["total_vulnerabilities"], 2)
        self.assertTrue(ScanFile.objects.filter(scan_id=response.data["id"]).exists())

    def test_anonymous_access_is_rejected(self):
        response = self.client.get(reverse("api:scan-list"))
        self.assertIn(response.status_code, (401, 403))
