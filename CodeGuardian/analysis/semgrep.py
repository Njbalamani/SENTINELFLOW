"""Optional Semgrep integration using a local rule configuration only."""
import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("codeguardian")

SEVERITY_MAP = {"ERROR": "HIGH", "WARNING": "MEDIUM", "INFO": "LOW"}


def scan(root: Path, config_path: str, timeout: int = 60) -> list[dict]:
    executable = shutil.which("semgrep")
    if not executable or not Path(config_path).exists():
        return []
    command = [
        executable,
        "scan",
        "--config",
        str(config_path),
        "--json",
        "--quiet",
        str(root),
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
        payload = json.loads(completed.stdout or "{}")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        logger.warning("Semgrep scan unavailable: %s", exc)
        return []

    findings = []
    for item in payload.get("results", []):
        extra = item.get("extra", {})
        metadata = extra.get("metadata", {}) or {}
        start = item.get("start", {}) or {}
        try:
            relative = Path(item["path"]).resolve().relative_to(root.resolve()).as_posix()
        except (KeyError, ValueError):
            relative = Path(item.get("path", "unknown")).name
        check_id = item.get("check_id", "semgrep.unknown")
        findings.append(
            {
                "rule_id": f"SEMGREP-{check_id.split('.')[-1]}",
                "title": f"Semgrep: {check_id.split('.')[-1].replace('-', ' ')}",
                "severity": SEVERITY_MAP.get(extra.get("severity", "INFO"), "LOW"),
                "category": metadata.get("category", "Semgrep Finding"),
                "owasp": metadata.get("owasp", "A04:2021 Insecure Design"),
                "line": int(start.get("line") or 1),
                "column": int(start.get("col") or 1),
                "code_snippet": (extra.get("lines") or "").strip()[:500],
                "description": extra.get("message", "Semgrep matched a risky pattern."),
                "impact": metadata.get("impact", "This pattern may introduce a security weakness."),
                "remediation": metadata.get("remediation", "Apply the secure coding pattern for this rule."),
                "corrected_code": metadata.get("corrected_code", "Use a validated, safe API instead."),
                "confidence": "high",
                "detector": "SEMGREP",
                "file_path": relative,
            }
        )
    return findings
