from django.conf import settings
from django.db import models

from apps.monitoring.models import UserActivity


class Classification(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    SUSPICIOUS = "SUSPICIOUS", "Suspicious"
    CRITICAL = "CRITICAL", "Critical"


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class DetectionResult(models.Model):
    activity = models.OneToOneField(UserActivity, on_delete=models.CASCADE, related_name="detection")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="detections")
    model_name = models.CharField(max_length=32, default="RULE_BASED")
    classification = models.CharField(max_length=16, choices=Classification.choices, db_index=True)
    risk_score = models.FloatField(default=0, db_index=True)
    anomaly_score = models.FloatField(default=0)
    confidence = models.FloatField(default=0)
    reasons = models.JSONField(default=list, blank=True)
    features = models.JSONField(default=dict, blank=True)
    models_agreed = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["classification", "created_at"]),
            models.Index(fields=["user", "risk_score"]),
        ]

    @property
    def severity_class(self):
        return {
            Classification.NORMAL: "success",
            Classification.SUSPICIOUS: "warning",
            Classification.CRITICAL: "danger",
        }.get(self.classification, "muted")

    def __str__(self):
        return f"{self.user.username} · {self.classification} ({self.risk_score:.0f})"


class UserRiskProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="risk_profile")
    risk_score = models.FloatField(default=0, db_index=True)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.choices, default=RiskLevel.LOW, db_index=True)
    total_activities = models.PositiveIntegerField(default=0)
    suspicious_count = models.PositiveIntegerField(default=0)
    critical_count = models.PositiveIntegerField(default=0)
    failed_logins_24h = models.PositiveIntegerField(default=0)
    downloads_24h = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-risk_score"]

    @property
    def level_class(self):
        return {
            RiskLevel.LOW: "success",
            RiskLevel.MEDIUM: "warning",
            RiskLevel.HIGH: "danger",
            RiskLevel.CRITICAL: "critical",
        }.get(self.risk_level, "muted")

    def __str__(self):
        return f"{self.user.username} · {self.risk_level} ({self.risk_score:.0f})"


class DetectionModelRun(models.Model):
    model_name = models.CharField(max_length=64)
    samples = models.PositiveIntegerField(default=0)
    accuracy = models.FloatField(null=True, blank=True)
    weighted_f1 = models.FloatField(null=True, blank=True)
    artifact_path = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    trained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trained_at"]

    def __str__(self):
        return f"{self.model_name} · {self.trained_at:%Y-%m-%d %H:%M}"
