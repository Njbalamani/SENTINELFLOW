import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Max, Q
from django.utils import timezone

from apps.core.models import log_audit
from ml.predict import predict
from .features import build_feature_vector
from .models import Classification, DetectionModelRun, DetectionResult, RiskLevel, UserRiskProfile

logger = logging.getLogger("sentinelflow")


def risk_level_for(score):
    config = settings.SENTINELFLOW
    if score >= config["RISK_HIGH_THRESHOLD"]:
        return RiskLevel.CRITICAL if score >= 85 else RiskLevel.HIGH
    if score >= config["RISK_MEDIUM_THRESHOLD"]:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def analyze_activity(activity):
    """Score a single activity, persist the result, update risk and raise alerts."""
    features = build_feature_vector(activity)
    prediction = predict(features)
    result, _ = DetectionResult.objects.update_or_create(
        activity=activity,
        defaults={
            "user": activity.user,
            "model_name": prediction["model"],
            "classification": prediction["classification"],
            "risk_score": prediction["risk_score"],
            "anomaly_score": prediction["anomaly_score"],
            "confidence": prediction["confidence"],
            "reasons": prediction.get("reasons", []),
            "features": {key: round(float(value), 4) for key, value in features.items()},
            "models_agreed": prediction.get("models_agreed"),
        },
    )
    update_risk_profile(activity.user)
    if result.classification in {Classification.SUSPICIOUS, Classification.CRITICAL}:
        try:
            from apps.alerts.services import create_alert_from_detection

            create_alert_from_detection(result)
        except Exception as exc:
            logger.exception("Failed to raise alert for detection %s: %s", result.pk, exc)
    return result


def update_risk_profile(user):
    since = timezone.now() - timedelta(days=30)
    stats = DetectionResult.objects.filter(user=user, created_at__gte=since).aggregate(
        average=Avg("risk_score"),
        maximum=Max("risk_score"),
        total=Count("id"),
        suspicious=Count("id", filter=Q(classification=Classification.SUSPICIOUS)),
        critical=Count("id", filter=Q(classification=Classification.CRITICAL)),
    )
    average, maximum = stats["average"] or 0, stats["maximum"] or 0
    score = min(100.0, 0.65 * average + 0.35 * maximum + min(10, stats["critical"] * 2))
    from apps.monitoring.models import ActivityType, UserActivity

    activity_stats = UserActivity.objects.filter(user=user, timestamp__gte=since).aggregate(
        failed=Count("id", filter=Q(activity_type=ActivityType.FAILED_LOGIN)),
        downloads=Count("id", filter=Q(activity_type=ActivityType.DOWNLOAD)),
        last=Max("timestamp"),
    )
    profile, _ = UserRiskProfile.objects.update_or_create(
        user=user,
        defaults={
            "risk_score": round(score, 2),
            "risk_level": risk_level_for(score),
            "total_activities": stats["total"],
            "suspicious_count": stats["suspicious"],
            "critical_count": stats["critical"],
            "failed_logins_24h": activity_stats["failed"],
            "downloads_24h": activity_stats["downloads"],
            "last_activity_at": activity_stats["last"],
        },
    )
    return profile


def recalculate_all_profiles():
    from django.contrib.auth import get_user_model

    return [update_risk_profile(user) for user in get_user_model().objects.filter(is_active=True)]


def sync_model_metadata(actor=None):
    """Record the latest trained artifacts as an active model run."""
    directory = settings.ML_ARTIFACT_DIR
    metadata_path = directory / "metadata.json"
    if not metadata_path.exists():
        return None
    import json

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    run, _ = DetectionModelRun.objects.update_or_create(
        model_name="HYBRID_RF_IFOREST",
        is_active=True,
        defaults={
            "samples": metadata.get("samples", 0),
            "accuracy": metadata.get("accuracy"),
            "weighted_f1": metadata.get("weighted_f1"),
            "artifact_path": str(directory),
            "notes": f"sklearn {metadata.get('sklearn_version', 'unknown')}",
        },
    )
    log_audit(
        action="TRAIN", entity_type="DETECTION_MODEL", entity_id=run.pk, actor=actor,
        details={"samples": run.samples, "accuracy": run.accuracy},
    )
    return run
