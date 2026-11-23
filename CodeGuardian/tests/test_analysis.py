from pathlib import Path

from django.test import TestCase, override_settings

from analysis import engine, rules

TEST_CONFIG = {
    "MAX_FILE_SIZE_MB": 10,
    "MAX_ZIP_SIZE_MB": 25,
    "MAX_UNCOMPRESSED_ZIP_MB": 100,
    "MAX_FILES_PER_ZIP": 200,
    "ALLOWED_EXTENSIONS": {".py", ".js", ".jsx", ".ts", ".tsx", ".java"},
    "ALLOWED_LANGUAGES": {"python", "javascript", "java"},
    "SCAN_TIMEOUT_SECONDS": 60,
    "ENABLE_AI_EXPLANATIONS": False,
    "GEMINI_API_KEY": "",
    "GEMINI_MODEL": "gemini-1.5-flash",
    "AI_TIMEOUT_SECONDS": 15,
    "BANDIT_ENABLED": False,
    "SEMGREP_ENABLED": False,
    "SEMGREP_CONFIG": "",
}


@override_settings(CODEGUARDIAN=TEST_CONFIG)
class AnalysisTests(TestCase):
    def test_language_for_extension(self):
        self.assertEqual(rules.language_for("app.py"), "python")
        self.assertEqual(rules.language_for("app.tsx"), "javascript")
        self.assertEqual(rules.language_for("Main.java"), "java")
        self.assertEqual(rules.language_for("notes.txt"), "")

    def test_custom_rule_detects_sql_injection(self):
        source = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
        findings = rules.scan_text(source, "python")
        self.assertTrue(any(item["rule_id"] == "CG-SQLI-002" for item in findings))

    def test_custom_rule_detects_dom_xss(self):
        findings = rules.scan_text("element.innerHTML = userInput;", "javascript")
        self.assertTrue(any(item["rule_id"] == "CG-XSS-001" for item in findings))

    def test_deduplicate_keeps_one_per_rule_and_line(self):
        finding = {"file_path": "a.py", "rule_id": "CG-XSS-001", "line": 4}
        self.assertEqual(len(engine.deduplicate([finding, dict(finding)])), 1)

    def test_security_score_is_severity_weighted(self):
        findings = [{"severity": "CRITICAL"}, {"severity": "HIGH"}, {"severity": "MEDIUM"}]
        self.assertEqual(engine.security_score(findings), 65)

    def test_explanations_are_grounded_without_ai(self):
        finding = {
            "rule_id": "CG-SQLI-002",
            "title": "SQL injection",
            "severity": "CRITICAL",
            "owasp": "A03:2021 Injection",
            "description": "SQL injection via interpolated SQL.",
        }
        explained = engine.analyze_paths.__globals__["ai"].deterministic_explanation(finding)
        self.assertEqual(explained["explanation_source"], "RULE_BASED")
        self.assertIn("SQL injection", explained["description"])
