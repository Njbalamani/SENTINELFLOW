"""Load synthetic activity events into the database and run the detection pipeline."""
import csv
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.alerts.models import SecurityAlert
from apps.detection.services import analyze_activity, recalculate_all_profiles, sync_model_metadata
from apps.investigation.services import create_case_from_alert
from apps.monitoring.models import ActivitySource, UserActivity
from apps.monitoring.services import is_off_hours

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with synthetic users and activity events (never real employee data)."

    def add_arguments(self, parser):
        parser.add_argument("--activities", type=int, default=300)
        parser.add_argument("--dataset", default=str(settings.BASE_DIR / "data" / "sample_user_activity.csv"))
        parser.add_argument("--password", default=None)

    def handle(self, *args, **options):
        path = Path(options["dataset"])
        if not path.exists():
            self.stderr.write(f"Dataset not found: {path}. Run: python -m ml.generate_dataset")
            return
        password = options["password"] or "Sentinel@2026!"
        self._demo_users(password)

        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        rows = rows[: max(0, options["activities"])]
        created = 0
        for row in rows:
            user = User.objects.filter(username=row["username"]).first()
            if not user:
                continue
            moment = datetime.fromisoformat(row["timestamp"])
            if timezone.is_naive(moment):
                moment = timezone.make_aware(moment)
            activity, was_created = UserActivity.objects.get_or_create(
                user=user,
                activity_type=row["activity_type"],
                timestamp=moment,
                resource=row["resource"],
                defaults={
                    "ip_address": row["ip_address"],
                    "bytes_transferred": int(row["bytes_transferred"]),
                    "is_off_hours": bool(int(row["off_hours"])),
                    "is_unusual_location": bool(int(row["unusual_location"])),
                    "source": ActivitySource.SYNTHETIC,
                    "metadata": {"synthetic": True, "dataset_label": row["label"]},
                },
            )
            if was_created:
                analyze_activity(activity)
                created += 1

        recalculate_all_profiles()
        run = sync_model_metadata()
        cases = 0
        for alert in SecurityAlert.objects.filter(
            severity__in=["CRITICAL", "HIGH"], investigation__isnull=True
        )[:3]:
            create_case_from_alert(alert)
            cases += 1
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} synthetic activities, {cases} investigation cases. "
            f"Active model: {run.model_name if run else 'rule-based'}."
        ))
        self.stdout.write(self.style.WARNING("Demo password: " + password + " — change it before any real deployment."))

    def _demo_users(self, password):
        accounts = [
            ("sentinel_admin", "ADMIN", "admin@sentinelflow.local", "Platform Administrator"),
            ("sentinel_analyst", "ANALYST", "analyst@sentinelflow.local", "Security Analyst"),
            ("sentinel_viewer", "VIEWER", "viewer@sentinelflow.local", "Compliance Viewer"),
        ]
        for username, role, email, title in accounts:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "email": email, "job_title": title, "department": "IT"},
            )
            user.set_password(password)
            user.is_active = True
            user.is_staff = role == "ADMIN"
            user.is_superuser = role == "ADMIN"
            user.save()
        with (settings.BASE_DIR / "data" / "sample_user_activity.csv").open(newline="", encoding="utf-8") as handle:
            names = {row["username"] for row in csv.DictReader(handle)}
        for name in sorted(names):
            user, _ = User.objects.get_or_create(
                username=name, defaults={"department": "OPERATIONS", "role": "VIEWER"}
            )
            user.set_password(password)
            user.is_active = True
            user.save()
