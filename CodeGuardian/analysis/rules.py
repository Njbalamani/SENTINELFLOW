"""Custom static-analysis rules for CODEGUARDIAN.

Rules are regex based and inspect source text only. Uploaded code is never executed.
"""
from dataclasses import dataclass, field
from pathlib import Path
import re

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".java": "java",
}


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str
    category: str
    owasp: str
    description: str
    impact: str
    remediation: str
    corrected_code: str
    confidence: str = "high"
    patterns: tuple[tuple[str, str], ...] = field(default_factory=tuple)


RULES = [
    Rule(
        id="CG-SQLI-001",
        title="SQL injection via string concatenation",
        severity="CRITICAL",
        category="SQL Injection",
        owasp="A03:2021 Injection",
        description="A SQL query is built by concatenating untrusted input into the query string. The database cannot distinguish code from data, so an attacker can alter the query.",
        impact="Unauthorised data access, authentication bypass, data modification, or full database compromise.",
        remediation="Use parameterised queries or prepared statements. Never concatenate request input into SQL text.",
        corrected_code="# Python (DB-API)\ncursor.execute(\"SELECT * FROM users WHERE name = %s\", (username,))",
        patterns=(
            ("python", r"SELECT\s+.*?WHERE\s+.*?[\"']\s*\+\s*\w+"),
            ("javascript", r"(?:query|sql)\s*=\s*[\"'`].*?[\"'`]\s*\+\s*\w+"),
            ("java", r"(?:String\s+)?(?:query|sql)\s*=\s*.*\+.*\w+"),
        ),
    ),
    Rule(
        id="CG-SQLI-002",
        title="SQL injection via f-string or template interpolation",
        severity="CRITICAL",
        category="SQL Injection",
        owasp="A03:2021 Injection",
        description="Untrusted values are interpolated directly into a SQL statement using an f-string or template literal.",
        impact="Attackers can inject arbitrary SQL, bypass authentication, or exfiltrate data.",
        remediation="Pass values as query parameters instead of interpolating them into SQL text.",
        corrected_code="cursor.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,))",
        patterns=(
            ("python", r"(?:execute|raw)\s*\(\s*f[\"'].*\{.*\}"),
            ("javascript", r"(?:query|sql)\s*=\s*`.*\$\{.*\}.*`"),
            ("java", r"String\s+query\s*=\s*String\.format\(.*SELECT"),
        ),
    ),
    Rule(
        id="CG-XSS-001",
        title="DOM-based cross-site scripting",
        severity="HIGH",
        category="Cross-Site Scripting",
        owasp="A03:2021 Injection",
        description="Untrusted data is written directly into the DOM using an HTML sink such as innerHTML or document.write.",
        impact="Session theft, credential harvesting, defacement, or client-side redirection.",
        remediation="Use textContent or a sanitizer. Never insert unsanitised input into HTML sinks.",
        corrected_code="element.textContent = userInput;",
        patterns=(
            ("javascript", r"\.innerHTML\s*="),
            ("javascript", r"document\.write\s*\("),
            ("javascript", r"dangerouslySetInnerHTML\s*="),
            ("javascript", r"v-html\s*="),
        ),
    ),
    Rule(
        id="CG-XSS-002",
        title="Unescaped server-side template rendering",
        severity="HIGH",
        category="Cross-Site Scripting",
        owasp="A03:2021 Injection",
        description="User-controlled content is passed into a dynamic server-side template, which can execute template expressions.",
        impact="Server-side template injection and reflected XSS.",
        remediation="Use static templates with autoescaping and pass user values as context variables.",
        corrected_code="return render_template('profile.html', name=user_input)",
        patterns=(("python", r"render_template_string\s*\("),),
    ),
    Rule(
        id="CG-SECRET-001",
        title="Hardcoded credential or API secret",
        severity="CRITICAL",
        category="Hardcoded Credentials",
        owasp="A07:2021 Identification and Authentication Failures",
        description="A password, token, API key, or secret is embedded as a literal in source code.",
        impact="Anyone with repository access can retrieve the credential; rotation is difficult and leaks are permanent in history.",
        remediation="Load secrets from environment variables or a managed secret store and rotate exposed values.",
        corrected_code="api_key = os.environ['API_KEY']",
        patterns=(
            ("python", r"(?i)(password|passwd|secret|api_key|apikey|access_token)\s*[:=]\s*[\"'][^\"']{4,}[\"']"),
            ("javascript", r"(?i)(password|secret|apiKey|token)\s*[:=]\s*[\"'][^\"']{4,}[\"']"),
            ("java", r"(?i)(password|secret|apiKey)\s*=\s*[\"'][^\"']{4,}[\"']"),
        ),
    ),
    Rule(
        id="CG-SECRET-002",
        title="Hardcoded cloud access key",
        severity="CRITICAL",
        category="Sensitive Information Exposure",
        owasp="A02:2021 Cryptographic Failures",
        description="A cloud provider access key identifier is present in source code.",
        impact="Direct account compromise and unauthorised resource access.",
        remediation="Revoke the key immediately and use instance roles or environment-based credentials.",
        corrected_code="credentials = boto3.Session().get_credentials()",
        patterns=(("python", r"AKIA[0-9A-Z]{16}"), ("javascript", r"AKIA[0-9A-Z]{16}"), ("java", r"AKIA[0-9A-Z]{16}")),
    ),
    Rule(
        id="CG-SECRET-003",
        title="Embedded private key",
        severity="CRITICAL",
        category="Sensitive Information Exposure",
        owasp="A02:2021 Cryptographic Failures",
        description="A PEM-formatted private key is embedded in source code.",
        impact="Attackers can impersonate the service, decrypt traffic, or sign arbitrary tokens.",
        remediation="Store private keys in a secret manager or secure file store with strict permissions.",
        corrected_code="private_key = load_key_from_secret_store('signing-key')",
        patterns=(("python", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),),
    ),
    Rule(
        id="CG-CRYPTO-001",
        title="Weak hash algorithm (MD5)",
        severity="HIGH",
        category="Insecure Cryptography",
        owasp="A02:2021 Cryptographic Failures",
        description="MD5 is used for a security-sensitive hash. It is collision-prone and unsuitable for passwords or signatures.",
        impact="Hash collisions, credential cracking, and integrity bypass.",
        remediation="Use SHA-256 for integrity and Argon2/bcrypt/scrypt for passwords.",
        corrected_code="hashed = hashlib.sha256(data).hexdigest()",
        patterns=(
            ("python", r"hashlib\.md5\s*\("),
            ("javascript", r"crypto\.createHash\([\"']md5[\"']"),
            ("java", r"MessageDigest\.getInstance\([\"']MD5[\"']"),
        ),
    ),
    Rule(
        id="CG-CRYPTO-002",
        title="Weak hash algorithm (SHA-1)",
        severity="MEDIUM",
        category="Insecure Cryptography",
        owasp="A02:2021 Cryptographic Failures",
        description="SHA-1 is deprecated for collision-resistant security use.",
        impact="Signature or certificate collision attacks.",
        remediation="Use SHA-256 or stronger for signatures and integrity checks.",
        corrected_code="digest = hashlib.sha256(payload).digest()",
        patterns=(
            ("python", r"hashlib\.sha1\s*\("),
            ("javascript", r"crypto\.createHash\([\"']sha1[\"']"),
            ("java", r"MessageDigest\.getInstance\([\"']SHA-1[\"']"),
        ),
    ),
    Rule(
        id="CG-CRYPTO-003",
        title="Insecure random number generation",
        severity="HIGH",
        category="Insecure Cryptography",
        owasp="A02:2021 Cryptographic Failures",
        description="A non-cryptographic random generator is used for a security-sensitive value such as a token or nonce.",
        impact="Predictable secrets, session tokens, or reset links.",
        remediation="Use a cryptographically secure generator such as secrets.token_urlsafe or SecureRandom.",
        corrected_code="token = secrets.token_urlsafe(32)",
        patterns=(
            ("python", r"random\.(?:random|randint|choice)\s*\("),
            ("javascript", r"Math\.random\s*\("),
            ("java", r"new\s+Random\s*\("),
        ),
    ),
    Rule(
        id="CG-DESER-001",
        title="Insecure deserialization",
        severity="CRITICAL",
        category="Insecure Deserialization",
        owasp="A08:2021 Software and Data Integrity Failures",
        description="Untrusted data is deserialized with a mechanism that can instantiate arbitrary objects or execute constructors.",
        impact="Remote code execution, authentication bypass, or data tampering.",
        remediation="Avoid native deserialization of untrusted data. Use JSON with strict schemas and safe loaders.",
        corrected_code="data = yaml.safe_load(raw)",
        patterns=(
            ("python", r"pickle\.loads?\s*\("),
            ("python", r"yaml\.load\s*\((?![^)]*SafeLoader)"),
            ("javascript", r"unserialize\s*\("),
            ("java", r"ObjectInputStream"),
        ),
    ),
    Rule(
        id="CG-CMD-001",
        title="Command injection",
        severity="CRITICAL",
        category="Command Injection",
        owasp="A03:2021 Injection",
        description="A system command is built from untrusted input or executed through a shell.",
        impact="Arbitrary operating-system command execution and full host compromise.",
        remediation="Avoid shell invocation. Use argument arrays and strict input validation or allowlists.",
        corrected_code="subprocess.run(['ping', '-c', '1', host], check=True, shell=False)",
        patterns=(
            ("python", r"os\.system\s*\("),
            ("python", r"subprocess\.(?:call|run|Popen)\([^)]*shell\s*=\s*True"),
            ("javascript", r"child_process\.exec\s*\("),
            ("java", r"Runtime\.getRuntime\(\)\.exec\s*\("),
        ),
    ),
    Rule(
        id="CG-AUTH-001",
        title="Weak authentication comparison",
        severity="HIGH",
        category="Weak Authentication",
        owasp="A07:2021 Identification and Authentication Failures",
        description="Secrets are compared with a plain equality operator, which may leak timing information, or TLS verification is disabled.",
        impact="Credential oracle, man-in-the-middle attacks, or authentication bypass.",
        remediation="Use constant-time comparison functions and keep certificate verification enabled.",
        corrected_code="hmac.compare_digest(submitted, stored_hash)",
        patterns=(
            ("python", r"(?i)password\s*==|==\s*[^\n]*password"),
            ("python", r"verify\s*=\s*False"),
            ("javascript", r"rejectUnauthorized\s*:\s*false"),
            ("java", r"setHostnameVerifier\s*\(\s*\(\w+,\s*\w+\)\s*->\s*true"),
        ),
    ),
    Rule(
        id="CG-LOG-001",
        title="Sensitive information written to logs",
        severity="MEDIUM",
        category="Sensitive Information Exposure",
        owasp="A09:2021 Security Logging and Monitoring Failures",
        description="A password, token, or secret appears in a logging or printing statement.",
        impact="Credential leakage into log files and downstream monitoring systems.",
        remediation="Redact sensitive fields before logging and use structured logging with allowlisted fields.",
        corrected_code="logger.info('login attempt for user=%s', username)",
        patterns=(
            ("python", r"(?:print|logger\.\w+)\s*\(.*(?i)(password|secret|token)"),
            ("javascript", r"console\.\w+\s*\(.*(?i)(password|secret|token)"),
        ),
    ),
    Rule(
        id="CG-CFG-001",
        title="Debug mode enabled",
        severity="MEDIUM",
        category="Security Misconfiguration",
        owasp="A05:2021 Security Misconfiguration",
        description="Debug mode is enabled, which can expose stack traces and interactive consoles.",
        impact="Information disclosure and potential remote code execution through debug tooling.",
        remediation="Disable debug mode in any shared or production environment.",
        corrected_code="DEBUG = False",
        patterns=(
            ("python", r"DEBUG\s*=\s*True"),
            ("javascript", r"debug\s*:\s*true"),
        ),
    ),
    Rule(
        id="CG-PATH-001",
        title="Potential path traversal",
        severity="HIGH",
        category="Path Traversal",
        owasp="A01:2021 Broken Access Control",
        description="User-controlled input is used in a filesystem path without visible canonicalisation or containment checks.",
        impact="Arbitrary file read or overwrite outside the intended directory.",
        remediation="Resolve the final path and verify it stays inside an allowed base directory before use.",
        corrected_code="path = (BASE / user_value).resolve()\nif not path.is_relative_to(BASE): raise ValueError('Invalid path')",
        patterns=(
            ("python", r"os\.path\.join\s*\([^)]*request"),
            ("javascript", r"path\.join\s*\([^)]*req\."),
            ("java", r"new\s+File\s*\([^)]*request"),
        ),
    ),
]

SEVERITY_WEIGHTS = {
    "CRITICAL": 20,
    "HIGH": 10,
    "MEDIUM": 5,
    "LOW": 2,
    "INFO": 0,
}


def language_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return LANGUAGE_BY_EXTENSION.get(suffix, "")


def finding_from_rule(rule: Rule, line: int, snippet: str, column: int = 1) -> dict:
    return {
        "rule_id": rule.id,
        "title": rule.title,
        "severity": rule.severity,
        "category": rule.category,
        "owasp": rule.owasp,
        "line": line,
        "column": column,
        "code_snippet": snippet.strip()[:500],
        "description": rule.description,
        "impact": rule.impact,
        "remediation": rule.remediation,
        "corrected_code": rule.corrected_code,
        "confidence": rule.confidence,
        "detector": "CUSTOM",
    }


def scan_text(text: str, language: str) -> list[dict]:
    """Scan a single source text and return raw finding dictionaries."""
    findings = []
    lines = text.splitlines()
    for rule in RULES:
        patterns = [pattern for lang, pattern in rule.patterns if lang == language]
        for pattern in patterns:
            try:
                regex = re.compile(pattern)
            except re.error:
                continue
            for index, line in enumerate(lines, start=1):
                match = regex.search(line)
                if match:
                    findings.append(
                        finding_from_rule(rule, index, line, match.start() + 1)
                    )
                    break
    return findings
