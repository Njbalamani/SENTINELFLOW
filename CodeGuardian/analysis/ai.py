"""Optional Gemini-powered explanations.

AI is called only for findings that static analysis already produced. It explains and
recommends; it never decides whether a vulnerability exists.
"""
import json
import logging
import urllib.request

logger = logging.getLogger("codeguardian")


def deterministic_explanation(finding: dict) -> dict:
    description = finding.get("description", "Static analysis flagged this pattern.")
    remediation = finding.get("remediation", "Apply the secure alternative for this pattern.")
    return {
        "description": description,
        "explanation": description,
        "impact": finding.get("impact", "This pattern may expose the application to attack."),
        "remediation": remediation,
        "recommendation": remediation,
        "corrected_code": finding.get("corrected_code", ""),
        "explanation_source": "RULE_BASED",
    }


def _gemini_explanation(finding: dict, api_key: str, model: str, timeout: int) -> dict:
    prompt = (
        "You are a senior application security engineer. Explain this static-analysis "
        "finding and recommend a secure fix. Do not invent additional findings.\n\n"
        f"Rule: {finding.get('rule_id')}\n"
        f"Title: {finding.get('title')}\n"
        f"File: {finding.get('file_path')} line {finding.get('line')}\n"
        f"Code: {finding.get('code_snippet')}\n"
        f"Description: {finding.get('description')}\n"
        f"Impact: {finding.get('impact')}\n"
        f"Baseline remediation: {finding.get('remediation')}\n\n"
        "Return strict JSON with keys: explanation, impact, recommendation, corrected_code."
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip().removeprefix("```json").removesuffix("```").strip()
    data = json.loads(text)
    explanation = str(data.get("explanation", ""))[:2000] or finding.get("description", "")
    recommendation = str(data.get("recommendation", ""))[:1500] or finding.get("remediation", "")
    return {
        "description": explanation,
        "explanation": explanation,
        "impact": str(data.get("impact", ""))[:1000] or finding.get("impact", ""),
        "remediation": recommendation,
        "recommendation": recommendation,
        "corrected_code": str(data.get("corrected_code", ""))[:2000],
        "explanation_source": "GEMINI",
    }


def explain_finding(
    finding: dict,
    enabled: bool = False,
    api_key: str = "",
    model: str = "gemini-1.5-flash",
    timeout: int = 15,
) -> dict:
    fallback = deterministic_explanation(finding)
    if not enabled or not api_key:
        return fallback
    try:
        enriched = _gemini_explanation(finding, api_key, model, timeout)
        logger.info("Gemini explanation generated for %s", finding.get("rule_id"))
        return enriched
    except Exception as exc:
        logger.warning("Gemini explanation failed, using rules: %s", exc)
        return fallback
