from datetime import datetime

from django.core.files.base import ContentFile

from apps.core.models import log_audit
from .models import GeneratedReport
from .pdf import BUILDERS


def generate_report(report_type, *, generated_by=None, title=None, alert=None, user=None, case=None, days=14,
                    parameters=None):
    """Build a PDF, persist it and return the GeneratedReport record."""
    builder = BUILDERS.get(report_type)
    if builder is None:
        raise ValueError(f"Unsupported report type: {report_type}")
    if report_type == GeneratedReport.ReportType.ALERT and alert is None:
        raise ValueError("An alert is required for an alert report.")
    if report_type == GeneratedReport.ReportType.ACTIVITY and user is None:
        raise ValueError("A user is required for an activity report.")
    if report_type == GeneratedReport.ReportType.INVESTIGATION and case is None:
        raise ValueError("An investigation case is required for an investigation report.")

    content = builder(alert=alert, user=user, case=case, days=days)
    label = GeneratedReport.ReportType(report_type).label
    suffix = alert.pk if alert else (user.username if user else (case.short_id if case else "all"))
    report = GeneratedReport(
        title=title or f"{label} — {suffix}",
        report_type=report_type,
        generated_by=generated_by,
        parameters=parameters or {},
        record_count=len(content) // 1024,
    )
    filename = f"sentinelflow_{str(report_type).lower()}_{suffix}_{datetime.now():%Y%m%d%H%M%S}.pdf"
    report.file.save(filename, ContentFile(content), save=True)
    log_audit(
        action="EXPORT", entity_type="GENERATED_REPORT", entity_id=report.pk, actor=generated_by,
        details={"report_type": report_type, "title": report.title},
    )
    return report
