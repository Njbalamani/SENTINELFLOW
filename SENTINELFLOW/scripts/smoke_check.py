"""Smoke-check every major web page and API route against a seeded database."""
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]
client = Client()
admin = get_user_model().objects.filter(role="ADMIN", is_superuser=True).first()
if not admin:
    raise SystemExit("No admin account found. Run: python manage.py seed_synthetic_data")

client.force_login(admin)
paths = [
    "/dashboard/", "/dashboard/analytics/", "/monitoring/", "/monitoring/new/",
    "/detection/", "/detection/risk/", "/detection/models/", "/alerts/",
    "/investigations/", "/investigations/new/", "/reports/", "/reports/generate/",
    "/accounts/users/", "/accounts/register/", "/accounts/profile/", "/audit/",
    "/api/v1/activities/", "/api/v1/detections/", "/api/v1/risk-profiles/",
    "/api/v1/alerts/", "/api/v1/investigations/", "/api/v1/models/",
    "/api/v1/users/", "/api/v1/analytics/summary/", "/health/",
]
failures = []
for path in paths:
    try:
        response = client.get(path)
        status = response.status_code
        print(f"{status} {path}")
        if status >= 400:
            failures.append((path, status))
    except Exception as exc:
        print(f"EXC {path}: {exc}")
        failures.append((path, str(exc)))

for path in ["/detection/1/", "/detection/risk/1/", "/monitoring/1/", "/alerts/1/", "/investigations/1/"]:
    response = client.get(path)
    print(f"{response.status_code} {path}")
    if response.status_code >= 400:
        failures.append((path, response.status_code))

if failures:
    raise SystemExit(f"Smoke check failed: {failures}")
print("All smoke checks passed.")
