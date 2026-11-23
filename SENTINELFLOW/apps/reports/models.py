import uuid

from django.conf import settings
from django.db import models


def report_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"reports/{instance.report_type.lower()}_{uuid.uuid4().hex[:12]}.{extension}"


class GeneratedReport(models.Model):
    class ReportType(models.TextChoices):
        ALERT = "ALERT", "Alert report"
        RISK = "RISK", "Risk assessment"
        ACTIVITY = "ACTIVITY", "Activity history"
        INVESTIGATION = "INVESTIGATION", "Investigation report"

    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=24, choices=ReportType.choices)
    format = models.CharField(max_length=8, default="PDF")
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="reports"
    )
    file = models.FileField(upload_to=report_upload_path)
    parameters = models.JSONField(default=dict, blank=True)
    record_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.format})"
