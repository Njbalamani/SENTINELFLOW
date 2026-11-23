import uuid

from django.conf import settings
from django.db import models


class CaseStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    CLOSED = "CLOSED", "Closed"


class CasePriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class InvestigationCase(models.Model):
    case_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=200)
    alert = models.OneToOneField(
        "alerts.SecurityAlert", on_delete=models.SET_NULL, null=True, blank=True, related_name="investigation"
    )
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="investigations_as_subject"
    )
    status = models.CharField(max_length=16, choices=CaseStatus.choices, default=CaseStatus.OPEN, db_index=True)
    priority = models.CharField(max_length=16, choices=CasePriority.choices, default=CasePriority.MEDIUM)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assigned_cases",
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="opened_cases",
    )
    activities = models.ManyToManyField("monitoring.UserActivity", blank=True, related_name="cases")
    findings = models.TextField(blank=True)
    conclusion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def status_class(self):
        return {
            CaseStatus.OPEN: "danger", CaseStatus.IN_PROGRESS: "warning", CaseStatus.CLOSED: "success",
        }.get(self.status, "muted")

    @property
    def short_id(self):
        return str(self.case_id)[:8].upper()

    def __str__(self):
        return f"{self.short_id} · {self.title}"


class InvestigationNote(models.Model):
    case = models.ForeignKey(InvestigationCase, on_delete=models.CASCADE, related_name="case_notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="case_notes")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Note on {self.case.short_id}"
