from django.conf import settings
from django.utils import timezone


def sentinel_context(request):
    """Lightweight, globally available template context."""
    context = {
        "app_name": "SENTINELFLOW",
        "app_tagline": "AI-Powered Insider Threat Detection",
        "current_year": timezone.now().year,
        "app_version": settings.SENTINELFLOW_VERSION,
    }
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        context.update(
            {
                "user_role": getattr(user, "role", ""),
                "is_admin": user.role == "ADMIN" if hasattr(user, "role") else user.is_staff,
                "is_analyst": hasattr(user, "role") and user.role in {"ADMIN", "ANALYST"},
            }
        )
        try:
            from apps.alerts.models import SecurityAlert

            context["open_alert_count"] = SecurityAlert.objects.filter(
                status__in=[SecurityAlert.Status.OPEN, SecurityAlert.Status.INVESTIGATING]
            ).count()
        except Exception:
            context["open_alert_count"] = 0
    return context
