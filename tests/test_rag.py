"""RAG tests.  Run:  python -m unittest discover tests"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vaccine"))

import debug  # noqa: E402
import rag  # noqa: E402


class Tokens(unittest.TestCase):
    def test_code_aware_tokens(self):
        # camelCase and snake_case are split; "get" and "or" are stopwords
        self.assertEqual(rag.tokens("billingCity get_or_create_nest"), ["billing", "city", "create", "nest"])

    def test_plurals_and_stopwords(self):
        self.assertEqual(rag.tokens("the totals of invoices"), ["total", "invoice"])


class Retrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("git"):
            raise unittest.SkipTest("needs git")
        cls.tmp = Path(tempfile.mkdtemp())
        cls.repo = cls.tmp / "demo-repo"
        subprocess.run([sys.executable, "demo/build_demo_repo.py", str(cls.repo)], cwd=ROOT, check=True, capture_output=True)
        chunks = (rag.chunks_from_repo(cls.repo, "invoice-kit")
                  + rag.chunks_from_antigens(ROOT / "examples/mutants.example.json", "invoice-kit")
                  + rag.chunks_from_antigens(ROOT / "case-studies/tomli/mutants.json", "tomli"))
        cls.index = rag.build_index(chunks)
        cls.kb = debug.learn([("invoice-kit", ROOT / "examples/mutants.example.json"),
                              ("tomli", ROOT / "case-studies/tomli/mutants.json")])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, onerror=lambda f, p, _: (Path(p).chmod(0o666), f(p)))

    def test_index_covers_fixes_postmortems_and_patterns(self):
        kinds = {c["kind"] for c in self.index["chunks"]}
        self.assertEqual(kinds, {"fix", "postmortem", "pattern"})
        self.assertEqual([c["id"] for c in self.index["chunks"]], list(range(1, len(self.index["chunks"]) + 1)))

    def test_crash_retrieves_the_postmortem_first(self):
        hits = rag.search("nightly job crashed: Cannot read properties of undefined (reading 'city')", self.index["chunks"])
        self.assertEqual(hits[0]["chunk"]["kind"], "postmortem")
        self.assertIn("#57", hits[0]["chunk"]["title"])

    def test_hybrid_finds_the_pattern_with_no_shared_words(self):
        q = "why does the PDF show 0.30000000000000004?"
        plain = [h["chunk"]["ref"] for h in rag.search(q, self.index["chunks"])]
        hybrid = rag.hybrid_search(q, self.index["chunks"], self.kb)
        self.assertNotIn("invoice-kit:A63", plain[:1])
        self.assertEqual(hybrid[0]["chunk"]["ref"], "invoice-kit:A63")
        self.assertIn("signature", hybrid[0]["matched"])

    def test_grounded_prompt_numbers_sources_and_demands_citations(self):
        hits = rag.search("invoice totals off by a cent", self.index["chunks"], k=2)
        p = rag.grounded_prompt("invoice totals off by a cent", hits)
        self.assertIn("[1] ", p)
        self.assertIn("[2] ", p)
        self.assertIn("cite them", p)
        self.assertIn("Our history doesn't cover this", p)

    def test_no_match_says_so(self):
        self.assertEqual(rag.search("zzzz qqqq", self.index["chunks"]), [])
        self.assertIn("no company sources matched", rag.grounded_prompt("zzzz", []))

    def test_index_redacts_secrets(self):
        idx = rag.build_index([{"kind": "doc", "repo": "x", "ref": "r", "title": "t",
                                "text": 'DB_PASSWORD="Tr0ub4dor&3horse"'}])
        self.assertNotIn("Tr0ub4dor", json.dumps(idx))


class PrConfigGuard(unittest.TestCase):
    """A PR that edits .bugvaccine/config.json must not get its new test command executed."""

    def test_pr_mode_refuses_a_pr_that_changes_the_test_command(self):
        if not shutil.which("node") or not shutil.which("git"):
            self.skipTest("needs node and git")
        tmp = Path(tempfile.mkdtemp())
        try:
            repo = tmp / "r"
            subprocess.run([sys.executable, "demo/build_demo_repo.py", str(repo)], cwd=ROOT, check=True, capture_output=True)
            bv = [sys.executable, str(ROOT / "bugvaccine.py")]
            subprocess.run(bv + ["init", str(repo), "--test", "npm test --silent"], check=True, capture_output=True)
            shutil.copy(ROOT / "examples/mutants.example.json", repo / ".bugvaccine/mutants.json")
            g = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
            subprocess.run(g + ["add", "-A"], check=True)
            subprocess.run(g + ["commit", "-qm", "add bug vaccine"], check=True)
            subprocess.run(g + ["checkout", "-qb", "evil"], check=True)
            cfg = repo / ".bugvaccine/config.json"
            data = json.loads(cfg.read_text(encoding="utf-8"))
            marker = tmp / "pwned.txt"
            data["test"] = f'python -c "open(r\'{marker}\', \'w\').write(\'x\')"'
            cfg.write_text(json.dumps(data), encoding="utf-8")
            subprocess.run(g + ["commit", "-qam", "innocent change"], check=True)

            r = subprocess.run(bv + ["pr", str(repo), "--base", "main"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertIn("REFUSED", r.stdout)
            self.assertFalse(marker.exists(), "the PR's test command must not have run")
        finally:
            shutil.rmtree(tmp, onerror=lambda f, p, _: (Path(p).chmod(0o666), f(p)))


if __name__ == "__main__":
    unittest.main()
