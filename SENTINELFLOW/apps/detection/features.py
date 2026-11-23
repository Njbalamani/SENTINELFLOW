from datetime import timedelta
import math

from django.db.models import Q, Sum
from django.utils import timezone

from ml.features import ACTIVITY_WEIGHTS, ROLE_WEIGHTS
from apps.monitoring.models import ActivityType, UserActivity, UserSession


def build_feature_vector(activity):
    """Derive the shared ML feature vector from stored activity history."""
    now = activity.timestamp
    recent = UserActivity.objects.filter(user=activity.user, timestamp__lte=now, timestamp__gte=now - timedelta(hours=1))
    day = UserActivity.objects.filter(user=activity.user, timestamp__lte=now, timestamp__gte=now - timedelta(hours=24))

    failed = recent.filter(activity_type=ActivityType.FAILED_LOGIN).count()
    downloads = recent.filter(activity_type=ActivityType.DOWNLOAD).count()
    accesses = recent.filter(activity_type=ActivityType.FILE_ACCESS).count()
    unique_resources = recent.exclude(resource="").values("resource").distinct().count()
    transferred = recent.filter(activity_type=ActivityType.DOWNLOAD).aggregate(total=Sum("bytes_transferred"))["total"] or 0
    privilege_changes = day.filter(
        activity_type__in=[ActivityType.PRIVILEGE_CHANGE, ActivityType.CONFIG_CHANGE]
    ).count()

    session = (
        UserSession.objects.filter(user=activity.user, login_at__lte=now)
        .filter(Q(logout_at__isnull=True) | Q(logout_at__gte=now))
        .order_by("-login_at")
        .first()
    )
    session_minutes = min(600, session.duration_minutes) if session else 0

    local_now = timezone.localtime(now) if timezone.is_aware(now) else now
    hour = local_now.hour
    angle = 2 * math.pi * hour / 24
    tenure = max(0, (now.date() - activity.user.date_joined.date()).days)

    return {
        "off_hours": int(hour < 7 or hour >= 19 or bool(activity.is_off_hours)),
        "failed_logins_1h": failed,
        "download_count_1h": downloads,
        "file_access_count_1h": accesses,
        "unique_resources_1h": unique_resources,
        "log_bytes_1h": math.log1p(transferred),
        "privilege_changes_24h": privilege_changes,
        "session_duration_minutes": session_minutes,
        "user_tenure_days": tenure,
        "role_risk_weight": ROLE_WEIGHTS.get(activity.user.role, 1.0),
        "activity_risk_weight": ACTIVITY_WEIGHTS.get(activity.activity_type, 1.0),
        "unusual_location": int(activity.is_unusual_location),
        "hour_sin": math.sin(angle),
        "hour_cos": math.cos(angle),
    }
