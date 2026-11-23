import logging

from .models import log_audit

logger = logging.getLogger("sentinelflow")

SENSITIVE_FIELDS = {
    "password", "password1", "password2", "old_password", "new_password1",
    "new_password2", "csrfmiddlewaretoken", "token", "secret", "api_key",
}

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIP_PREFIXES = ("/admin/", "/api-auth/", "/static/", "/media/", "/health/")


class AuditRequestMiddleware:
    """Records state-changing web requests for accountability and forensics."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._audit(request, response)
        except Exception as exc:
            logger.warning("Audit middleware failed: %s", exc)
        return response

    def _audit(self, request, response):
        if request.method not in WRITE_METHODS:
            return
        if request.path.startswith(SKIP_PREFIXES):
            return
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return
        if response.status_code >= 400:
            return
        payload = {
            key: ("[redacted]" if key.lower() in SENSITIVE_FIELDS else str(value)[:200])
            for key, value in request.POST.items()
        }
        log_audit(
            action="UPDATE" if request.method in {"PUT", "PATCH"} else "CREATE",
            entity_type="HTTP_REQUEST",
            entity_id=request.path,
            actor=user,
            ip_address=_client_ip(request),
            path=request.path,
            details={"method": request.method, "status": response.status_code, "fields": payload},
        )


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.META.get("REMOTE_ADDR") or None
