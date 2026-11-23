RECOMMENDATIONS = [
    {
        "owasp": "A01:2021 Broken Access Control",
        "title": "Enforce deny-by-default access control",
        "summary": "Verify authorisation on every request and scope records to the authenticated user.",
        "guidelines": [
            "Use object-level checks on every detail and update endpoint.",
            "Deny by default; allow only explicit roles or owners.",
            "Invalidate sessions on logout and password change.",
        ],
        "secure_example": "if finding.scan.owner != request.user:\n    raise PermissionDenied()",
    },
    {
        "owasp": "A02:2021 Cryptographic Failures",
        "title": "Protect secrets and use modern cryptography",
        "summary": "Never hardcode secrets, and use vetted algorithms with secure key management.",
        "guidelines": [
            "Load secrets from environment variables or a managed secret store.",
            "Use Argon2, bcrypt, or scrypt for passwords; SHA-256+ for integrity.",
            "Use secrets.token_urlsafe or SecureRandom for tokens.",
        ],
        "secure_example": "api_key = os.environ['API_KEY']\ntoken = secrets.token_urlsafe(32)",
    },
    {
        "owasp": "A03:2021 Injection",
        "title": "Separate code from data",
        "summary": "Use parameterised queries, safe DOM APIs, and avoid shell invocation.",
        "guidelines": [
            "Pass SQL values as bound parameters, never string concatenation.",
            "Use textContent or sanitizers instead of innerHTML.",
            "Avoid shell=True; pass argument arrays to subprocess.",
        ],
        "secure_example": "cursor.execute('SELECT * FROM users WHERE name = %s', (username,))",
    },
    {
        "owasp": "A05:2021 Security Misconfiguration",
        "title": "Harden defaults",
        "summary": "Disable debug mode, set security headers, and remove unnecessary services.",
        "guidelines": [
            "Keep DEBUG=False outside local development.",
            "Set HSTS, secure cookies, X-Frame-Options, and CSRF origins.",
            "Run scanners and linters in CI to catch unsafe defaults.",
        ],
        "secure_example": "DEBUG = False\nSECURE_SSL_REDIRECT = True",
    },
    {
        "owasp": "A07:2021 Identification and Authentication Failures",
        "title": "Strengthen authentication",
        "summary": "Use strong password storage, MFA, and constant-time comparisons.",
        "guidelines": [
            "Hash passwords with a slow adaptive hash.",
            "Use hmac.compare_digest for secret comparison.",
            "Rotate and revoke exposed credentials immediately.",
        ],
        "secure_example": "if hmac.compare_digest(submitted, stored_hash):\n    login(request, user)",
    },
    {
        "owasp": "A08:2021 Software and Data Integrity Failures",
        "title": "Deserialize safely",
        "summary": "Avoid object deserialisation of untrusted data and verify artifact integrity.",
        "guidelines": [
            "Use JSON with strict schemas instead of pickle or native serialisation.",
            "Use yaml.safe_load for YAML input.",
            "Sign and verify build artifacts before deployment.",
        ],
        "secure_example": "data = yaml.safe_load(raw_yaml)",
    },
    {
        "owasp": "A09:2021 Security Logging and Monitoring Failures",
        "title": "Log safely and monitor deliberately",
        "summary": "Record security-relevant events without leaking sensitive data.",
        "guidelines": [
            "Never log passwords, tokens, or full request bodies.",
            "Log actor, action, entity, timestamp, and source IP.",
            "Alert on repeated failures and unusual administrative actions.",
        ],
        "secure_example": "logger.info('login failed for user=%s', username)",
    },
]
