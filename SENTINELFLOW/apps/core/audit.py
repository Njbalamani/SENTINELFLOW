import ipaddress

from django.utils import timezone

from .models import AuditLog


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidate = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def record_audit(request=None, *, actor=None, action, target_model="", target_id="", details=None, ip_address=None):
    """Create an audit entry without ever storing request bodies or secrets."""
    payload = {}
    if isinstance(details, dict):
        for key, value in details.items():
            if str(key).lower() in {"password", "password1", "password2", "token", "secret", "key"}:
                continue
            payload[str(key)] = str(value)[:500]

    kwargs = {
        "action": action,
        "target_model": target_model[:100],
        "target_id": str(target_id)[:64],
        "details": payload,
        "created_at": timezone.now(),
    }
    if request is not None:
        kwargs["ip_address"] = client_ip(request)
        kwargs["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:1000]
        if actor is None:
            actor = getattr(request, "user", None)
        if actor is not None and getattr(actor, "is_authenticated", False):
            kwargs["actor"] = actor
            kwargs["actor_username"] = actor.get_username()
    elif actor is not None and getattr(actor, "is_authenticated", False):
        kwargs["actor"] = actor
        kwargs["actor_username"] = actor.get_username()
    if ip_address is not None:
        kwargs["ip_address"] = ip_address
    return AuditLog.objects.create(**kwargs)
