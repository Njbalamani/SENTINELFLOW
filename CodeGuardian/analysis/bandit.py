"""Bandit integration. Bandit reads files; it never executes uploaded code."""
import json
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("codeguardian")

SEVERITY_MAP = {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"}
RECOMMENDATIONS = {
    "B301": "Avoid pickle/marshal for untrusted data; use JSON with a strict schema.",
    "B302": "Avoid marshal for untrusted data; use JSON with a strict schema.",
    "B303": "Use SHA-256 or Argon2 instead of MD5/SHA1.",
    "B311": "Use the secrets module or os.urandom for security-sensitive randomness.",
    "B602": "Avoid shell=True. Pass an argument list and validate input.",
    "B603": "Pass an argument list and avoid untrusted command components.",
    "B608": "Use parameterised SQL queries instead of string building.",
}


def _owasp_for(test_id: str) -> str:
    if test_id.startswith(("B6", "B3")):
        return "A03:2021 Injection"
    if test_id.startswith("B1"):
        return "A05:2021 Security Misconfiguration"
    return "A04:2021 Insecure Design"


def scan(paths: list[Path], root: Path, timeout: int = 60) -> list[dict]:
    if not paths:
        return []
    command = [sys.executable, "-m", "bandit", "-q", "-f", "json"]
    command.extend(str(path) for path in paths)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        payload = json.loads(completed.stdout or "{}")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        logger.warning("Bandit scan unavailable: %s", exc)
        return []

    findings = []
    for item in payload.get("results", []):
        test_id = item.get("test_id", "B000")
        try:
            relative = Path(item["filename"]).resolve().relative_to(root.resolve()).as_posix()
        except (KeyError, ValueError):
            relative = Path(item.get("filename", "unknown")).name
        findings.append(
            {
                "rule_id": f"BANDIT-{test_id}",
                "title": f"Bandit {test_id}: {item.get('issue_text', 'Security issue')}",
                "severity": SEVERITY_MAP.get(item.get("issue_severity", "LOW"), "LOW"),
                "category": "Bandit Finding",
                "owasp": _owasp_for(test_id),
                "line": int(item.get("line_number") or 1),
                "column": int(item.get("col_offset") or 1),
                "code_snippet": (item.get("code") or "").strip()[:500],
                "description": item.get("issue_text", "Bandit identified a potential security weakness."),
                "impact": "This pattern is known to be exploitable in security-sensitive contexts.",
                "remediation": RECOMMENDATIONS.get(
                    test_id,
                    "Review the Bandit guidance for this test and apply the secure alternative.",
                ),
                "corrected_code": RECOMMENDATIONS.get(test_id, "Replace the flagged pattern with a safer API."),
                "confidence": str(item.get("issue_confidence", "MEDIUM")).lower(),
                "detector": "BANDIT",
            }
        )
        findings[-1]["file_path"] = relative
    return findings
