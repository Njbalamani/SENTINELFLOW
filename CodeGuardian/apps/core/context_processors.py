from django.conf import settings
from django.utils import timezone


def codeguardian_context(request):
    context = {
        "app_name": "CODEGUARDIAN",
        "app_tagline": "AI-Powered Secure Code Review",
        "app_version": settings.CODEGUARDIAN_VERSION,
        "current_year": timezone.now().year,
    }
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        try:
            from apps.scan.models import Scan

            context["scan_count"] = Scan.objects.filter(owner=user).count()
        except Exception:
            context["scan_count"] = 0
    return context
