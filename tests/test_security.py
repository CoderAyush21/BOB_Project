"""Security tests.  Run:  python -m unittest discover tests"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vaccine"))

import redact  # noqa: E402

# Obviously fake credentials, built at runtime so secret scanners don't flag this file.
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
FAKE_GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
FAKE_JWT = "eyJ" + "hbGciOiJIUzI1NiJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkwIn0" + "." + "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"


class Redaction(unittest.TestCase):
    def test_known_token_formats_are_redacted(self):
        for secret, rule in [(FAKE_AWS, "aws-access-key"), (FAKE_GH, "github-token"), (FAKE_JWT, "jwt")]:
            with self.subTest(rule=rule):
                out, counts = redact.redact(f"value = {secret} end")
                self.assertNotIn(secret, out)
                self.assertIn(rule, counts)

    def test_assigned_secrets_keep_the_name_but_lose_the_value(self):
        for line in ['IBM_CLOUD_API_KEY="Zx9' + 'kLmNoPqRsTuVwXyZ012345"', "password: hunter2hunter2",
                     "db_password = 'S3cr3tValue!'", "apikey=abcdef1234567890"]:
            with self.subTest(line=line):
                out = redact.redact_text(line)
                self.assertIn("[REDACTED:assigned-secret]", out)
                self.assertNotRegex(out, r"Zx9|hunter2|S3cr3t|abcdef1234")

    def test_url_credentials_and_private_keys(self):
        out = redact.redact_text("postgres://admin:" + "sup3rs3cret@db.internal:5432/app")
        self.assertIn("admin:[REDACTED]@db.internal", out)
        key = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIEow" + "IBAAKCAQEA\n-----END RSA " + "PRIVATE KEY-----"
        self.assertEqual(redact.redact_text(key), "[REDACTED:private-key]")

    def test_ordinary_code_is_untouched(self):
        code = "const token = parseToken(header);\nif (password.length < 8) throw new Error('too short');"
        self.assertEqual(redact.redact_text(code), code)

    def test_rules_are_javascript_compatible(self):
        for name, pat, _flags, _how in redact.RULES:
            with self.subTest(rule=name):
                self.assertNotRegex(pat, r"\(\?P<|\(\?[aiLmsux]+\)")


class PathContainment(unittest.TestCase):
    def setUp(self):
        import run
        self.run = run
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "src" / "a.js").write_text("x = 1\n", encoding="utf-8")
        self.outside = self.tmp / "outside.txt"
        self.outside.write_text("do not touch\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_safe_path_accepts_files_inside_the_repo(self):
        self.assertEqual(self.run.safe_path(self.repo, "src/a.js"), (self.repo / "src" / "a.js").resolve())

    def test_traversal_and_absolute_paths_are_rejected(self):
        for bad in ["../outside.txt", "src/../../outside.txt", str(self.outside)]:
            with self.subTest(path=bad):
                with self.assertRaises(ValueError):
                    self.run.safe_path(self.repo, bad)

    def test_symlink_escaping_the_repo_is_rejected(self):
        link = self.repo / "src" / "link.txt"
        try:
            os.symlink(self.outside, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted on this machine")
        with self.assertRaises(ValueError):
            self.run.safe_path(self.repo, "src/link.txt")

    def test_runner_refuses_an_escaping_mutant_and_leaves_the_file_alone(self):
        mutants = [{"id": "X1", "antigen": "A", "file": "../outside.txt", "find": "do not touch", "replace": "pwned"}]
        results = self.run.run_mutants(mutants, self.repo, "exit 0", 30, log=lambda *_: None)
        self.assertEqual(results[0]["status"], "invalid")
        self.assertIn("outside the repository", results[0]["detail"])
        self.assertEqual(self.outside.read_text(encoding="utf-8"), "do not touch\n")


class RegexSafety(unittest.TestCase):
    def test_nested_quantifiers_are_rejected(self):
        import debug
        for bad in [r"(a+)+$", r"(\w+)*x", r"(.*)+", r"([a-z]+\s?)+end"]:
            with self.subTest(pattern=bad):
                self.assertTrue(debug.risky_regex(bad))
        for ok in [r"\.slice\([^)]*[+-]\s*1\s*\)", r"Cannot read propert(y|ies) of (undefined|null)", r"(abc)+"]:
            with self.subTest(pattern=ok):
                self.assertFalse(debug.risky_regex(ok))

    def test_learn_refuses_a_knowledge_base_with_a_risky_regex(self):
        import debug
        tmp = Path(tempfile.mkdtemp())
        try:
            f = tmp / "antigens.json"
            f.write_text(json.dumps({"antigens": [{"id": "Z", "title": "t", "pattern": "p",
                                                   "signatures": {"errors": ["(a+)+$"]}}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                debug.learn([("x", f)])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Dashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import dashboard
        cls.dashboard = dashboard
        evil = '"><img src=x onerror=alert(1)><script>alert(2)</script>'
        run = {"repo": "r", "label": "", "killed": evil, "total": 1, "immunity": evil, "timeouts": 0, "invalid": 0,
               "antigens": [{"id": "A1", "title": evil, "pattern": evil}],
               "results": [{"id": "M1", "antigen": "A1", "file": evil, "find": evil, "replace": evil, "why": evil, "status": evil}]}
        data = {"meta": {"repo": "r", "title": "T", "generated": "now"},
                "history": {"total": 0, "fixes": 0, "commits": [], "truncated": False, "incidents": []},
                "antigens": run["antigens"], "runs": {"before": run, "after": None, "holdout": None, "pr": None},
                "antibodies": [], "knowledge": None, "projects": [], "samples": {"diff": None},
                "rag": [{"id": 1, "kind": "fix", "ref": "x", "title": "t", "text": "password = " + "hunter2hunter2"}]}
        cls.html = dashboard.render(data)
        cls.html_fonts = dashboard.render(data, web_fonts=True)

    def test_data_block_cannot_break_out_of_its_script_tag(self):
        start = self.html.index('<script id="data" type="application/json">')
        block = self.html[start:self.html.index("</script>", start)]
        self.assertNotIn("<", block[len('<script id="data" type="application/json">'):])

    def test_strict_csp_with_script_hash_and_no_network(self):
        import base64
        import hashlib
        import re
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', self.html).group(1)
        self.assertIn("default-src 'none'", csp)
        self.assertIn("connect-src 'none'", csp)
        self.assertNotIn("unsafe-inline' ;", csp.replace("style-src 'unsafe-inline'", ""))
        body = re.search(r"<script>([\s\S]*?)</script>", self.html).group(1)
        digest = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode()
        self.assertIn(f"'sha256-{digest}'", csp)
        self.assertNotIn("fonts.googleapis.com", self.html)

    def test_web_fonts_are_opt_in_and_allowed_by_csp_only_then(self):
        self.assertIn("fonts.googleapis.com", self.html_fonts)
        self.assertIn("font-src https://fonts.gstatic.com", self.html_fonts)

    def test_secrets_in_embedded_knowledge_are_redacted(self):
        self.assertNotIn("hunter2hunter2", self.html)


if __name__ == "__main__":
    unittest.main()
