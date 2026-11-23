from django.db.models import Avg, Count

from apps.scan.models import Finding, Scan


SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


def dashboard_metrics(user):
    scans = Scan.objects.filter(owner=user)
    findings = Finding.objects.filter(scan__owner=user)
    counts = dict(findings.values_list("severity").annotate(total=Count("id")))
    severity_distribution = [
        {"severity": severity, "count": counts.get(severity, 0)} for severity in SEVERITIES
    ]
    return {
        "total_scans": scans.count(),
        "completed_scans": scans.filter(status=Scan.Status.COMPLETED).count(),
        "total_vulnerabilities": findings.count(),
        "critical_findings": counts.get("CRITICAL", 0),
        "high_findings": counts.get("HIGH", 0),
        "average_security_score": round(scans.aggregate(Avg("security_score"))["security_score__avg"] or 0, 1),
        "severity_distribution": severity_distribution,
        "recent_scans": list(scans.select_related("owner").order_by("-created_at")[:8]),
    }
