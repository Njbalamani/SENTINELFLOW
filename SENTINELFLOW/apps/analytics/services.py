from datetime import timedelta

from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.accounts.models import User
from apps.alerts.models import AlertStatus, SecurityAlert
from apps.detection.models import Classification, DetectionModelRun, DetectionResult, RiskLevel, UserRiskProfile
from apps.investigation.models import CaseStatus, InvestigationCase
from apps.monitoring.models import ActivityType, UserActivity


def _day_range(days):
    today = timezone.localdate()
    return [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]


def dashboard_stats(days=14):
    since = timezone.now() - timedelta(days=days)
    active_alerts = SecurityAlert.objects.filter(status__in=[AlertStatus.OPEN, AlertStatus.INVESTIGATING])
    profile_avg = UserRiskProfile.objects.aggregate(average=Avg("risk_score"))["average"] or 0
    return {
        "period_days": days,
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "monitored_users": User.objects.filter(activities__timestamp__gte=since).distinct().count(),
        "total_activities": UserActivity.objects.filter(timestamp__gte=since).count(),
        "suspicious_activities": DetectionResult.objects.filter(
            created_at__gte=since,
            classification__in=[Classification.SUSPICIOUS, Classification.CRITICAL],
        ).count(),
        "critical_activities": DetectionResult.objects.filter(
            created_at__gte=since, classification=Classification.CRITICAL
        ).count(),
        "open_alerts": active_alerts.count(),
        "critical_alerts": active_alerts.filter(severity="CRITICAL").count(),
        "resolved_alerts": SecurityAlert.objects.filter(
            status__in=[AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]
        ).count(),
        "open_cases": InvestigationCase.objects.exclude(status=CaseStatus.CLOSED).count(),
        "average_risk_score": round(profile_avg, 1),
        "active_model": DetectionModelRun.objects.filter(is_active=True).first(),
    }


def daily_activity(days=14):
    since = timezone.now() - timedelta(days=days)
    dates = _day_range(days)
    activities = {
        row["day"]: row["total"]
        for row in UserActivity.objects.filter(timestamp__gte=since)
        .annotate(day=TruncDate("timestamp")).values("day").annotate(total=Count("id"))
    }
    detections = {
        row["day"]: row["total"]
        for row in DetectionResult.objects.filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at")).values("day").annotate(total=Count("id"))
    }
    return {
        "labels": [day.strftime("%b %d") for day in dates],
        "activities": [activities.get(day, 0) for day in dates],
        "detections": [detections.get(day, 0) for day in dates],
    }


def risk_distribution():
    counts = {
        row["risk_level"]: row["total"]
        for row in UserRiskProfile.objects.values("risk_level").annotate(total=Count("id"))
    }
    colors = {"LOW": "#22d3a7", "MEDIUM": "#f5b73d", "HIGH": "#fb7a5c", "CRITICAL": "#ef4463"}
    return [
        {"label": label, "value": counts.get(level, 0), "color": colors[level]}
        for level, label in RiskLevel.choices
    ]


def alerts_by_severity():
    counts = {
        row["severity"]: row["total"]
        for row in SecurityAlert.objects.values("severity").annotate(total=Count("id"))
    }
    colors = {"LOW": "#22d3a7", "MEDIUM": "#f5b73d", "HIGH": "#fb7a5c", "CRITICAL": "#ef4463"}
    return [
        {"label": label, "value": counts.get(level, 0), "color": colors[level]}
        for level, label in [("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("CRITICAL", "Critical")]
    ]


def activity_breakdown(days=14):
    since = timezone.now() - timedelta(days=days)
    counts = {
        row["activity_type"]: row["total"]
        for row in UserActivity.objects.filter(timestamp__gte=since)
        .values("activity_type").annotate(total=Count("id"))
    }
    return [
        {"label": label, "value": counts.get(key, 0)}
        for key, label in ActivityType.choices
    ]


def top_risky_users(limit=8):
    return [
        {
            "username": profile.user.username,
            "display_name": profile.user.display_name,
            "department": profile.user.get_department_display(),
            "score": profile.risk_score,
            "level": profile.risk_level,
            "level_class": profile.level_class,
        }
        for profile in UserRiskProfile.objects.select_related("user").order_by("-risk_score")[:limit]
    ]


def recent_alerts(limit=6):
    return list(
        SecurityAlert.objects.select_related("user").order_by("-created_at")[:limit].values(
            "id", "title", "severity", "status", "risk_score", "created_at", "user__username"
        )
    )


def incident_timeline(user, limit=60):
    activities = (
        UserActivity.objects.filter(user=user).select_related("detection")[:limit]
    )
    return [
        {
            "timestamp": activity.timestamp,
            "type": activity.get_activity_type_display(),
            "resource": activity.resource,
            "classification": activity.detection.classification if hasattr(activity, "detection") else "NORMAL",
            "risk_score": activity.detection.risk_score if hasattr(activity, "detection") else 0,
        }
        for activity in activities
    ]
