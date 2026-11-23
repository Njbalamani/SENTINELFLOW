"""Static analysis orchestration for CODEGUARDIAN."""
import logging
from pathlib import Path

from . import ai, bandit, rules, semgrep

logger = logging.getLogger("codeguardian")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def deduplicate(findings: list[dict]) -> list[dict]:
    seen = {}
    for finding in findings:
        key = (
            finding.get("file_path", ""),
            finding.get("rule_id", ""),
            int(finding.get("line") or 0),
        )
        if key not in seen:
            seen[key] = finding
    return list(seen.values())


def analyze_paths(paths: list[Path], root: Path, config: dict) -> list[dict]:
    """Run all enabled static analysers against already-saved source files."""
    findings = []
    scanned = []
    for path in paths:
        language = rules.language_for(path.name)
        if not language:
            continue
        try:
            relative = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            relative = path.name
        text = _read_text(path)
        if not text.strip():
            continue
        scanned.append(path)
        for finding in rules.scan_text(text, language):
            finding["file_path"] = relative
            findings.append(finding)

    if config.get("BANDIT_ENABLED", True):
        findings.extend(bandit.scan(scanned, root, config.get("SCAN_TIMEOUT_SECONDS", 60)))
    if config.get("SEMGREP_ENABLED", False):
        findings.extend(
            semgrep.scan(
                root,
                config.get("SEMGREP_CONFIG", ""),
                config.get("SCAN_TIMEOUT_SECONDS", 60),
            )
        )

    findings = deduplicate(findings)
    findings.sort(
        key=lambda item: (
            -rules.SEVERITY_WEIGHTS.get(item.get("severity", "INFO"), 0),
            item.get("file_path", ""),
            int(item.get("line") or 0),
        )
    )

    for index, finding in enumerate(findings[:10]):
        enriched = ai.explain_finding(
            finding,
            enabled=config.get("ENABLE_AI_EXPLANATIONS", False),
            api_key=config.get("GEMINI_API_KEY", ""),
            model=config.get("GEMINI_MODEL", "gemini-1.5-flash"),
            timeout=config.get("AI_TIMEOUT_SECONDS", 15),
        )
        finding.update(enriched)
    for finding in findings[10:]:
        finding.update(ai.deterministic_explanation(finding))

    logger.info("Static analysis produced %d findings from %d files", len(findings), len(scanned))
    return findings


def security_score(findings: list[dict]) -> int:
    penalty = sum(
        rules.SEVERITY_WEIGHTS.get(finding.get("severity", "INFO"), 0)
        for finding in findings
    )
    return max(0, 100 - penalty)
