from django.conf import settings
from django.db import models


class Severity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class AlertStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    INVESTIGATING = "INVESTIGATING", "Investigating"
    RESOLVED = "RESOLVED", "Resolved"
    FALSE_POSITIVE = "FALSE_POSITIVE", "False positive"


class SecurityAlert(models.Model):
    Status = AlertStatus

    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)
    status = models.CharField(max_length=20, choices=AlertStatus.choices, default=AlertStatus.OPEN, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    activity = models.ForeignKey(
        "monitoring.UserActivity", null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts"
    )
    detection = models.ForeignKey(
        "detection.DetectionResult", null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_alerts"
    )
    risk_score = models.FloatField(default=0)
    evidence = models.JSONField(default=dict, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "severity"]),
            models.Index(fields=["user", "created_at"]),
        ]

    @property
    def severity_class(self):
        return {
            Severity.LOW: "success", Severity.MEDIUM: "warning",
            Severity.HIGH: "danger", Severity.CRITICAL: "critical",
        }.get(self.severity, "muted")

    @property
    def status_class(self):
        return {
            AlertStatus.OPEN: "danger", AlertStatus.INVESTIGATING: "warning",
            AlertStatus.RESOLVED: "success", AlertStatus.FALSE_POSITIVE: "muted",
        }.get(self.status, "muted")

    def __str__(self):
        return f"[{self.severity}] {self.title}"


class AlertNote(models.Model):
    alert = models.ForeignKey(SecurityAlert, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="alert_notes")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Note by {self.author.username if self.author else 'system'} on alert {self.alert_id}"
