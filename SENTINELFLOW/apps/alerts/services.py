import logging
from datetime import timedelta

from django.utils import timezone

from apps.core.models import log_audit
from .models import AlertNote, AlertStatus, SecurityAlert, Severity

logger = logging.getLogger("sentinelflow")

SEVERITY_MAP = {
    "NORMAL": Severity.LOW,
    "SUSPICIOUS": Severity.HIGH,
    "CRITICAL": Severity.CRITICAL,
}


def create_alert_from_detection(detection, *, actor=None):
    """Create one alert per anomaly burst, deduplicating near-identical events."""
    severity = SEVERITY_MAP.get(detection.classification, Severity.MEDIUM)
    window = timezone.now() - timedelta(minutes=15)
    existing = SecurityAlert.objects.filter(
        user=detection.user, severity=severity, created_at__gte=window,
        status__in=[AlertStatus.OPEN, AlertStatus.INVESTIGATING],
    ).order_by("-created_at").first()
    if existing:
        AlertNote.objects.create(
            alert=existing,
            note=f"Additional anomaly detected (score {detection.risk_score:.0f}) at "
                 f"{detection.activity.timestamp:%Y-%m-%d %H:%M}.",
        )
        return existing

    reasons = "; ".join(detection.reasons[:4]) or "Behavioural deviation from baseline."
    alert = SecurityAlert.objects.create(
        title=f"{detection.get_classification_display()} behaviour: {detection.user.display_name}",
        description=(
            f"Automated analysis classified this activity as {detection.classification.lower()} "
            f"with a risk score of {detection.risk_score:.0f}/100. Signals: {reasons}."
        ),
        severity=severity,
        user=detection.user,
        activity=detection.activity,
        detection=detection,
        risk_score=detection.risk_score,
        evidence={
            "reasons": detection.reasons,
            "model": detection.model_name,
            "confidence": detection.confidence,
            "activity_type": detection.activity.activity_type,
            "resource": detection.activity.resource,
            "ip_address": str(detection.activity.ip_address) if detection.activity.ip_address else None,
        },
    )
    log_audit(
        action="CREATE", entity_type="SECURITY_ALERT", entity_id=alert.pk, actor=actor,
        details={"severity": severity, "user": detection.user.username},
    )
    logger.info("Raised %s alert %s for %s", severity, alert.pk, detection.user.username)
    return alert


def change_status(alert, status, *, actor=None, notes="", ip_address=None):
    previous = alert.status
    alert.status = status
    alert.resolution_notes = notes or alert.resolution_notes
    if status in {AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE}:
        alert.resolved_at = timezone.now()
    else:
        alert.resolved_at = None
    if actor and not alert.assigned_to:
        alert.assigned_to = actor
    alert.save()
    log_audit(
        action="STATUS_CHANGE", entity_type="SECURITY_ALERT", entity_id=alert.pk, actor=actor,
        ip_address=ip_address, details={"from": previous, "to": status},
    )
    return alert
