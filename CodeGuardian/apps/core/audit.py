from .models import AuditLog


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def audit_action(request, action, entity_type="", entity_id="", details=None):
    user = getattr(request, "user", None)
    entry = AuditLog.objects.create(
        actor=user if user and user.is_authenticated else None,
        actor_username=getattr(user, "username", "") if user else "",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id or "")[:120],
        ip_address=client_ip(request),
        details=details or {},
    )
    request._audit_logged = True
    return entry
