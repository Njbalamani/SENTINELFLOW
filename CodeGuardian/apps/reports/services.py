import json
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse

from apps.scan.models import Scan

from .models import GeneratedReport


def scan_payload(scan: Scan) -> dict:
    return {
        "platform": "CODEGUARDIAN",
        "version": settings.CODEGUARDIAN_VERSION,
        "scan": {
            "id": str(scan.id),
            "name": scan.name,
            "status": scan.status,
            "original_filename": scan.original_filename,
            "source_type": scan.source_type,
            "files_scanned": scan.files_scanned,
            "lines_scanned": scan.lines_scanned,
            "security_score": scan.security_score,
            "created_at": scan.created_at.isoformat(),
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        },
        "severity_counts": scan.severity_counts(),
        "files": [
            {
                "path": item.relative_path,
                "language": item.language,
                "lines": item.line_count,
                "sha256": item.content_hash,
            }
            for item in scan.files.all()
        ],
        "findings": [
            {
                "rule_id": item.rule_id,
                "title": item.title,
                "severity": item.severity,
                "category": item.category,
                "owasp": item.owasp,
                "file": item.file_path,
                "line": item.line,
                "column": item.column,
                "code": item.code_snippet,
                "description": item.description,
                "impact": item.impact,
                "remediation": item.remediation,
                "corrected_code": item.corrected_code,
                "detector": item.detector,
                "explanation_source": item.explanation_source,
            }
            for item in scan.findings.all()
        ],
    }


def create_json_report(scan: Scan, owner) -> GeneratedReport:
    payload = scan_payload(scan)
    filename = f"codeguardian-scan-{scan.id}.json"
    directory = Path(settings.MEDIA_ROOT) / "reports"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report = GeneratedReport.objects.create(
        scan=scan,
        owner=owner,
        format=GeneratedReport.Format.JSON,
        file=f"reports/{filename}",
        filename=filename,
    )
    return report


def json_download_response(scan: Scan) -> HttpResponse:
    payload = scan_payload(scan)
    response = HttpResponse(
        json.dumps(payload, indent=2), content_type="application/json; charset=utf-8"
    )
    response["Content-Disposition"] = f'attachment; filename="codeguardian-scan-{scan.id}.json"'
    return response
