from django.conf import settings
from django.db import models


class ActivityType(models.TextChoices):
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    FAILED_LOGIN = "FAILED_LOGIN", "Failed login"
    FILE_ACCESS = "FILE_ACCESS", "File access"
    DOWNLOAD = "DOWNLOAD", "Download"
    UPLOAD = "UPLOAD", "Upload"
    PRIVILEGE_CHANGE = "PRIVILEGE_CHANGE", "Privilege change"
    CONFIG_CHANGE = "CONFIG_CHANGE", "Configuration change"


class ActivitySource(models.TextChoices):
    WEB = "WEB", "Web application"
    API = "API", "REST API"
    SYNTHETIC = "SYNTHETIC", "Synthetic dataset"
    INGESTION = "INGESTION", "SIEM ingestion"


class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions")
    session_key = models.CharField(max_length=128, unique=True)
    login_at = models.DateTimeField(db_index=True)
    logout_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-login_at"]

    @property
    def duration_minutes(self):
        if not self.logout_at:
            return 0
        return max(0, int((self.logout_at - self.login_at).total_seconds() // 60))

    def __str__(self):
        return f"{self.user.username} · {self.login_at:%Y-%m-%d %H:%M}"


class UserActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=24, choices=ActivityType.choices, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    resource = models.CharField(max_length=512, blank=True)
    action_detail = models.TextField(blank=True)
    bytes_transferred = models.PositiveBigIntegerField(default=0)
    session_key = models.CharField(max_length=128, blank=True, db_index=True)
    is_off_hours = models.BooleanField(default=False, db_index=True)
    is_unusual_location = models.BooleanField(default=False)
    source = models.CharField(max_length=16, choices=ActivitySource.choices, default=ActivitySource.WEB)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["activity_type", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.username} · {self.get_activity_type_display()} · {self.timestamp:%Y-%m-%d %H:%M}"

    @property
    def human_size(self):
        size = float(self.bytes_transferred)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}"
            size /= 1024
