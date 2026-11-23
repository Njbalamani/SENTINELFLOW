from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable-style record of security-relevant actions performed in the system."""

    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        VIEW = "VIEW", "View"
        STATUS_CHANGE = "STATUS_CHANGE", "Status change"
        EXPORT = "EXPORT", "Export"
        PREDICTION = "PREDICTION", "Prediction"
        TRAIN = "TRAIN", "Model training"
        DENIED = "DENIED", "Access denied"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=24, choices=Action.choices, db_index=True)
    entity_type = models.CharField(max_length=80, db_index=True)
    entity_id = models.CharField(max_length=80, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["action", "created_at"])]
        verbose_name = "audit log"
        verbose_name_plural = "audit logs"

    def __str__(self):
        return f"{self.get_action_display()} · {self.entity_type} · {self.created_at:%Y-%m-%d %H:%M}"


def log_audit(*, action, entity_type, entity_id="", actor=None, ip_address=None,
              path="", details=None, actor_username=""):
    """Single entry point for writing audit records; never raises to callers."""
    try:
        return AuditLog.objects.create(
            actor=actor,
            actor_username=actor_username or (getattr(actor, "username", "") or ""),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id or ""),
            ip_address=ip_address,
            path=path or "",
            details=details or {},
        )
    except Exception:
        return None
