"""PDF document builders built on ReportLab."""
from datetime import timedelta
from io import BytesIO

from django.utils import timezone

from apps.alerts.models import SecurityAlert
from apps.analytics import services as analytics
from apps.detection.models import DetectionResult, UserRiskProfile
from apps.investigation.models import InvestigationCase
from apps.monitoring.models import UserActivity
from apps.reports.models import GeneratedReport

BRAND = "#101a2e"
ACCENT = "#3d8bff"
MUTED = "#5c6b85"


def _pdf_modules():
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:  # pragma: no cover - dependency failure path
        raise RuntimeError("PDF generation requires reportlab. Install requirements.txt first.") from exc
    return colors, TA_LEFT, A4, ParagraphStyle, getSampleStyleSheet, mm, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _document(title, subtitle):
    colors, TA_LEFT, A4, ParagraphStyle, get_sample, mm, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle = _pdf_modules()
    base = get_sample()
    styles = {
        "title": ParagraphStyle("sfTitle", parent=base["Title"], fontSize=20, textColor=colors.HexColor(BRAND), spaceAfter=4),
        "subtitle": ParagraphStyle("sfSub", parent=base["Normal"], fontSize=10, textColor=colors.HexColor(MUTED), spaceAfter=14),
        "heading": ParagraphStyle("sfHead", parent=base["Heading2"], fontSize=13, textColor=colors.HexColor(ACCENT), spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("sfBody", parent=base["BodyText"], fontSize=9, leading=13, alignment=TA_LEFT),
    }
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm, title=title, author="SENTINELFLOW",
    )
    story = [
        Paragraph("SENTINELFLOW", styles["title"]),
        Paragraph(f"{subtitle}<br/>Generated: {timezone.now():%Y-%m-%d %H:%M UTC} · CONFIDENTIAL", styles["subtitle"]),
    ]
    return buffer, doc, story, styles, Paragraph, Spacer, Table, TableStyle, colors, mm


def _table(data, widths, Table, TableStyle, colors, mm):
    table = Table(data, colWidths=[width * mm for width in widths], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dfeb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fb")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _finish(buffer, doc, story):
    doc.build(story)
    return buffer.getvalue()


def alert_pdf(alert: SecurityAlert):
    buffer, doc, story, styles, Paragraph, Spacer, Table, TableStyle, colors, mm = _document(
        f"Alert {alert.pk}", "Security Alert Report"
    )
    story.append(Paragraph(f"Alert #{alert.pk} — {alert.title}", styles["heading"]))
    details = [
        ["Field", "Value"],
        ["Severity", alert.severity], ["Status", alert.status],
        ["Subject", alert.user.username], ["Risk score", f"{alert.risk_score:.1f}/100"],
        ["Created", f"{alert.created_at:%Y-%m-%d %H:%M UTC}"],
        ["Assigned to", alert.assigned_to.username if alert.assigned_to else "Unassigned"],
    ]
    story.append(_table(details, [45, 125], Table, TableStyle, colors, mm))
    story.append(Paragraph("Analysis summary", styles["heading"]))
    story.append(Paragraph(alert.description.replace("<", "&lt;"), styles["body"]))
    if alert.resolution_notes:
        story.append(Paragraph("Resolution notes", styles["heading"]))
        story.append(Paragraph(alert.resolution_notes.replace("<", "&lt;"), styles["body"]))
    return _finish(buffer, doc, story)


def risk_pdf():
    buffer, doc, story, styles, Paragraph, Spacer, Table, TableStyle, colors, mm = _document(
        "risk-assessment", "Organisational Risk Assessment"
    )
    stats = analytics.dashboard_stats()
    rows = [["Metric", "Value"]] + [
        [label, str(stats[key])] for key, label in [
            ("total_users", "Total users"), ("monitored_users", "Monitored users (14d)"),
            ("suspicious_activities", "Suspicious activities (14d)"), ("critical_activities", "Critical detections (14d)"),
            ("open_alerts", "Open alerts"), ("critical_alerts", "Critical alerts"),
            ("average_risk_score", "Average user risk score"),
        ]
    ]
    story.append(_table(rows, [110, 60], Table, TableStyle, colors, mm))
    story.append(Paragraph("Highest-risk users", styles["heading"]))
    user_rows = [["User", "Department", "Score", "Level"]] + [
        [item["display_name"], item["department"], f"{item['score']:.1f}", item["level"]]
        for item in analytics.top_risky_users(12)
    ]
    story.append(_table(user_rows, [50, 60, 25, 35], Table, TableStyle, colors, mm))
    return _finish(buffer, doc, story)


def activity_pdf(user, days=14):
    buffer, doc, story, styles, Paragraph, Spacer, Table, TableStyle, colors, mm = _document(
        f"activity-{user.username}", f"Activity History — {user.display_name}"
    )
    since = timezone.now() - timedelta(days=days)
    activities = UserActivity.objects.filter(user=user, timestamp__gte=since).select_related("detection")[:200]
    profile = UserRiskProfile.objects.filter(user=user).first()
    risk_level = profile.risk_level if profile else "N/A"
    risk_score = profile.risk_score if profile else 0
    story.append(Paragraph(
        f"User: {user.username} · Department: {user.get_department_display()} · "
        f"Risk: {risk_level} ({risk_score:.1f}/100)",
        styles["body"],
    ))
    rows = [["Timestamp", "Activity", "Resource", "IP", "Risk"]]
    for activity in activities:
        score = activity.detection.risk_score if hasattr(activity, "detection") else 0
        rows.append([
            f"{activity.timestamp:%Y-%m-%d %H:%M}", activity.get_activity_type_display(),
            (activity.resource or "-")[:38], str(activity.ip_address or "-"), f"{score:.0f}",
        ])
    story.append(_table(rows, [34, 30, 60, 28, 18], Table, TableStyle, colors, mm))
    return _finish(buffer, doc, story)


def investigation_pdf(case: InvestigationCase):
    buffer, doc, story, styles, Paragraph, Spacer, Table, TableStyle, colors, mm = _document(
        f"case-{case.short_id}", "Incident Investigation Report"
    )
    story.append(Paragraph(f"Case {case.short_id} — {case.title}", styles["heading"]))
    rows = [
        ["Field", "Value"],
        ["Case ID", str(case.case_id)], ["Status", case.status],
        ["Priority", case.priority], ["Subject", case.subject.username if case.subject else "-"],
        ["Analyst", case.assigned_to.username if case.assigned_to else "-"],
        ["Opened", f"{case.created_at:%Y-%m-%d %H:%M UTC}"],
    ]
    story.append(_table(rows, [45, 125], Table, TableStyle, colors, mm))
    story.append(Paragraph("Findings", styles["heading"]))
    story.append(Paragraph((case.findings or "No findings recorded.").replace("<", "&lt;"), styles["body"]))
    story.append(Paragraph("Conclusion", styles["heading"]))
    story.append(Paragraph((case.conclusion or "Investigation still in progress.").replace("<", "&lt;"), styles["body"]))
    story.append(Paragraph("Case notes", styles["heading"]))
    for note in case.case_notes.all():
        story.append(Paragraph(f"{note.created_at:%Y-%m-%d %H:%M} — {note.note}".replace("<", "&lt;"), styles["body"]))
    return _finish(buffer, doc, story)


BUILDERS = {
    GeneratedReport.ReportType.ALERT: lambda alert=None, **_: alert_pdf(alert),
    GeneratedReport.ReportType.RISK: lambda **_: risk_pdf(),
    GeneratedReport.ReportType.ACTIVITY: lambda user=None, days=14, **_: activity_pdf(user, days),
    GeneratedReport.ReportType.INVESTIGATION: lambda case=None, **_: investigation_pdf(case),
}
