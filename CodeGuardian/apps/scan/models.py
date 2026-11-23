import uuid

from django.conf import settings
from django.db import models


class Scan(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SCANNING = "SCANNING", "Scanning"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class SourceType(models.TextChoices):
        FILE = "FILE", "Single file"
        ZIP = "ZIP", "ZIP project"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scans")
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    source_type = models.CharField(max_length=10, choices=SourceType.choices, default=SourceType.FILE)
    original_filename = models.CharField(max_length=255)
    files_scanned = models.PositiveIntegerField(default=0)
    lines_scanned = models.PositiveIntegerField(default=0)
    total_vulnerabilities = models.PositiveIntegerField(default=0)
    security_score = models.PositiveIntegerField(default=100)
    tool_versions = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"

    def severity_counts(self):
        counts = dict(self.findings.values_list("severity").annotate(total=models.Count("id")))
        return {key: counts.get(key, 0) for key in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]}


class ScanFile(models.Model):
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="uploads/")
    relative_path = models.CharField(max_length=500)
    language = models.CharField(max_length=30, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    line_count = models.PositiveIntegerField(default=0)
    content_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["relative_path"]
        indexes = [models.Index(fields=["scan", "relative_path"])]

    def __str__(self):
        return self.relative_path


class Finding(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"
        INFO = "INFO", "Informational"

    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name="findings")
    source_file = models.ForeignKey(
        ScanFile, null=True, blank=True, on_delete=models.SET_NULL, related_name="findings"
    )
    rule_id = models.CharField(max_length=80)
    title = models.CharField(max_length=250)
    severity = models.CharField(max_length=12, choices=Severity.choices)
    category = models.CharField(max_length=100)
    owasp = models.CharField(max_length=120, blank=True)
    file_path = models.CharField(max_length=500)
    line = models.PositiveIntegerField(default=1)
    column = models.PositiveIntegerField(default=1)
    code_snippet = models.TextField(blank=True)
    description = models.TextField()
    impact = models.TextField(blank=True)
    remediation = models.TextField()
    corrected_code = models.TextField(blank=True)
    confidence = models.CharField(max_length=20, default="high")
    detector = models.CharField(max_length=20, default="CUSTOM")
    explanation_source = models.CharField(max_length=20, default="RULE_BASED")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-severity", "file_path", "line"]
        indexes = [
            models.Index(fields=["scan", "-severity"]),
            models.Index(fields=["rule_id"]),
        ]

    def __str__(self):
        return f"{self.rule_id} at {self.file_path}:{self.line}"
