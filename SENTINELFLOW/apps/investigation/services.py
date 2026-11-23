from django.utils import timezone

from apps.core.models import log_audit
from .models import CaseStatus, InvestigationCase, InvestigationNote


def create_case_from_alert(alert, *, actor=None, priority=None):
    case, created = InvestigationCase.objects.get_or_create(
        alert=alert,
        defaults={
            "title": f"Investigation: {alert.title[:150]}",
            "subject": alert.user,
            "assigned_to": actor,
            "opened_by": actor,
            "priority": priority or alert.severity,
            "findings": alert.description,
        },
    )
    if created:
        related = []
        if alert.activity_id:
            related.append(alert.activity_id)
        if related:
            case.activities.set(related)
        log_audit(
            action="CREATE", entity_type="INVESTIGATION_CASE", entity_id=case.pk, actor=actor,
            details={"alert": alert.pk, "subject": alert.user.username},
        )
    return case, created


def add_note(case, author, note):
    entry = InvestigationNote.objects.create(case=case, author=author, note=note.strip())
    if case.status == CaseStatus.OPEN:
        case.status = CaseStatus.IN_PROGRESS
        case.save(update_fields=["status", "updated_at"])
    return entry


def close_case(case, *, actor=None, conclusion=""):
    case.status = CaseStatus.CLOSED
    case.conclusion = conclusion or case.conclusion
    case.closed_at = timezone.now()
    case.save()
    if case.alert and case.alert.status != "RESOLVED":
        from apps.alerts.services import change_status

        change_status(case.alert, "RESOLVED", actor=actor, notes=conclusion)
    log_audit(
        action="STATUS_CHANGE", entity_type="INVESTIGATION_CASE", entity_id=case.pk, actor=actor,
        details={"status": CaseStatus.CLOSED},
    )
    return case
