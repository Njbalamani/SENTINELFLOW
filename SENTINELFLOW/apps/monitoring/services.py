import logging
from datetime import time

from django.utils import timezone

from apps.core.models import log_audit
from .models import ActivitySource, ActivityType, UserActivity

logger = logging.getLogger("sentinelflow")

OFF_HOURS_START = time(7, 0)
OFF_HOURS_END = time(19, 0)


def is_off_hours(moment=None):
    moment = moment or timezone.localtime()
    if moment.tzinfo is not None:
        moment = timezone.localtime(moment)
    return moment.time() < OFF_HOURS_START or moment.time() >= OFF_HOURS_END


def get_request_metadata(request):
    if request is None:
        return {}
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    return {
        "ip_address": ip[:45] if ip else None,
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
        "session_key": request.session.session_key if hasattr(request, "session") else "",
    }


def record_activity(user, activity_type, *, request=None, timestamp=None, resource="",
                    action_detail="", bytes_transferred=0, ip_address=None,
                    user_agent="", session_key="", is_unusual_location=False,
                    source=ActivitySource.WEB, metadata=None, analyze=True):
    """Record one activity and immediately run the detection pipeline on it."""
    meta = get_request_metadata(request)
    activity = UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        timestamp=timestamp or timezone.now(),
        ip_address=ip_address or meta.get("ip_address"),
        user_agent=user_agent or meta.get("user_agent", ""),
        resource=resource or "",
        action_detail=action_detail or "",
        bytes_transferred=max(0, int(bytes_transferred or 0)),
        session_key=session_key or meta.get("session_key", "") or "",
        is_off_hours=is_off_hours(timestamp),
        is_unusual_location=bool(is_unusual_location),
        source=source,
        metadata=metadata or {},
    )
    if analyze:
        try:
            from apps.detection.services import analyze_activity

            analyze_activity(activity)
        except Exception as exc:
            logger.exception("Detection pipeline failed for activity %s: %s", activity.pk, exc)
    return activity


def record_login(user, request):
    activity = record_activity(user, ActivityType.LOGIN, request=request)
    log_audit(
        action="LOGIN", entity_type="USER_SESSION", entity_id=user.pk,
        actor=user, ip_address=activity.ip_address, path=request.path,
    )
    return activity


def record_logout(user, request):
    activity = record_activity(user, ActivityType.LOGOUT, request=request)
    log_audit(
        action="LOGOUT", entity_type="USER_SESSION", entity_id=user.pk,
        actor=user, ip_address=activity.ip_address, path=request.path,
    )
    return activity


def record_failed_login(username, request):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(username__iexact=username).first()
    if not user:
        return None
    activity = record_activity(
        user, ActivityType.FAILED_LOGIN, request=request,
        action_detail="Failed authentication attempt",
    )
    log_audit(
        action="DENIED", entity_type="LOGIN_ATTEMPT", entity_id=user.pk,
        actor=user, ip_address=activity.ip_address, path=request.path,
        details={"username": username},
    )
    return activity
