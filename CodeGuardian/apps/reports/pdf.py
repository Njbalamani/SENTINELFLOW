from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import GeneratedReport
from .services import scan_payload


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CGTitle", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#22d3ee")))
    styles.add(ParagraphStyle(name="CGSub", parent=styles["Normal"], alignment=TA_CENTER, textColor=colors.HexColor("#64748b")))
    styles.add(ParagraphStyle(name="CGHeading", parent=styles["Heading2"], textColor=colors.HexColor("#0f766e"), spaceBefore=10))
    styles.add(ParagraphStyle(name="CGCode", parent=styles["Code"], fontSize=7.5, leading=10, textColor=colors.HexColor("#334155")))
    return styles


def create_pdf_report(scan, owner) -> GeneratedReport:
    payload = scan_payload(scan)
    filename = f"codeguardian-scan-{scan.id}.pdf"
    directory = Path(settings.MEDIA_ROOT) / "reports"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    styles = _styles()
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"CODEGUARDIAN Report - {scan.name}",
    )
    story = []
    story.append(Paragraph("CODEGUARDIAN", styles["CGTitle"]))
    story.append(Paragraph("AI-Powered Secure Code Review Report", styles["CGSub"]))
    story.append(Spacer(1, 8 * mm))

    meta = [
        ["Scan", escape(scan.name)],
        ["ID", str(scan.id)],
        ["Owner", escape(owner.username)],
        ["Source", escape(scan.original_filename)],
        ["Completed", scan.completed_at.strftime("%Y-%m-%d %H:%M UTC") if scan.completed_at else "-"],
        ["Security score", f"{scan.security_score}/100"],
        ["Total findings", str(scan.total_vulnerabilities)],
    ]
    table = Table(meta, colWidths=[40 * mm, 128 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 6 * mm))

    counts = payload["severity_counts"]
    story.append(Paragraph("Severity distribution", styles["CGHeading"]))
    count_rows = [["Severity", "Count"]] + [[key, str(value)] for key, value in counts.items()]
    count_table = Table(count_rows, colWidths=[90 * mm, 78 * mm])
    count_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(count_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Findings and remediation", styles["CGHeading"]))
    if not payload["findings"]:
        story.append(Paragraph("No vulnerabilities were identified by the enabled analysers.", styles["Normal"]))
    for index, item in enumerate(payload["findings"], start=1):
        if index > 1:
            story.append(PageBreak())
        story.append(Paragraph(f"{index}. {escape(item['title'])}", styles["Heading3"]))
        detail_rows = [
            ["Severity", escape(item["severity"])],
            ["Rule", escape(item["rule_id"])],
            ["Location", f"{escape(item['file'])}:{item['line']}"],
            ["Detector", escape(item["detector"])],
            ["OWASP", escape(item["owasp"])],
        ]
        detail_table = Table(detail_rows, colWidths=[35 * mm, 133 * mm])
        detail_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(detail_table)
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(f"<b>Why this matters:</b> {escape(item['description'])}", styles["Normal"]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"<b>Impact:</b> {escape(item['impact'])}", styles["Normal"]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"<b>Flagged code:</b>", styles["Normal"]))
        story.append(Paragraph(escape(item["code"] or "-").replace("\n", "<br/>"), styles["CGCode"]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"<b>Remediation:</b> {escape(item['remediation'])}", styles["Normal"]))
        if item["corrected_code"]:
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph("<b>Safer example:</b>", styles["Normal"]))
            story.append(Paragraph(escape(item["corrected_code"]).replace("\n", "<br/>"), styles["CGCode"]))

    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "Generated by CODEGUARDIAN using static analysis. AI explanations, when enabled, "
            "describe existing findings only.",
            styles["CGSub"],
        )
    )
    document.build(story)

    return GeneratedReport.objects.create(
        scan=scan,
        owner=owner,
        format=GeneratedReport.Format.PDF,
        file=f"reports/{filename}",
        filename=filename,
    )
