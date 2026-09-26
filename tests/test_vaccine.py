"""Tests for Bug Vaccine's own tooling.  Run:  python -m unittest discover tests"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vaccine"))

import mine  # noqa: E402
import run  # noqa: E402


class ApplyMutant(unittest.TestCase):
    def test_replaces_exactly_one_match(self):
        new, hits = run.apply_mutant("a + b - 1", "- 1", "")
        self.assertEqual((new, hits), ("a + b ", 1))

    def test_refuses_zero_matches(self):
        self.assertEqual(run.apply_mutant("abc", "xyz", "q"), (None, 0))

    def test_refuses_ambiguous_matches(self):
        self.assertEqual(run.apply_mutant("x x", "x", "y"), (None, 2))

    def test_multiline_find_matches_crlf_file(self):
        text = "const a = 1;\r\nreturn a;\r\n"
        new, hits = run.apply_mutant(text, "const a = 1;\nreturn a;", "return 2;\nreturn 3;")
        self.assertEqual(hits, 1)
        self.assertEqual(new, "return 2;\r\nreturn 3;\r\n")

    def test_lf_file_untouched_by_crlf_logic(self):
        new, _ = run.apply_mutant("a\nb\n", "a\nb", "c\nd")
        self.assertEqual(new, "c\nd\n")


class Classify(unittest.TestCase):
    def test_statuses(self):
        self.assertEqual(run.classify(0), "survived")
        self.assertEqual(run.classify(1), "killed")
        self.assertEqual(run.classify("timeout"), "timeout")

    def test_timeouts_count_as_caught_but_are_reported(self):
        results = [{"status": "killed"}, {"status": "timeout"}, {"status": "survived"}, {"status": "invalid"}]
        s = run.summarize("r", [], results)
        self.assertEqual((s["killed"], s["total"], s["timeouts"], s["invalid"], s["immunity"]), (2, 3, 1, 1, 67))


class Gate(unittest.TestCase):
    def s(self, results):
        return run.summarize("r", [], [{"status": x} for x in results])

    def test_passes_at_threshold(self):
        self.assertEqual(run.gate(self.s(["killed", "killed", "killed", "survived"]), 75), 0)

    def test_fails_below_threshold(self):
        self.assertEqual(run.gate(self.s(["killed", "survived"]), 75), 2)

    def test_stale_mutants_fail_even_at_full_immunity(self):
        self.assertEqual(run.gate(self.s(["killed", "invalid"]), 50), 2)

    def test_pr_touching_no_vaccinated_files_passes(self):
        self.assertEqual(run.gate(self.s([]), 90), 0)


class FixDetection(unittest.TestCase):
    def test_detects_fix_messages(self):
        for msg in ["fix: off by one", "fix(api)!: crash", "Fixes #12", "Resolves #7 in pagination",
                    "closes #3", "hotfix for invoices", "Revert \"add cache\"", "Bugfix: null check",
                    "feat: thing\n\nThis patches the crash from the incident"]:
            with self.subTest(msg=msg):
                self.assertTrue(mine.is_fix(msg))

    def test_ignores_non_fix_messages(self):
        for msg in ["feat: add prefix option", "docs: update README", "chore: bump deps", "refactor: rename suffix"]:
            with self.subTest(msg=msg):
                self.assertFalse(mine.is_fix(msg))

    def test_detects_test_files(self):
        self.assertTrue(mine.touches_tests(["src/a.js", "test/a.test.js"]))
        self.assertTrue(mine.touches_tests(["tests/test_money.py"]))
        self.assertFalse(mine.touches_tests(["src/a.js", "README.md"]))


class EndToEnd(unittest.TestCase):
    """Builds the demo repo and checks the vaccine's headline numbers."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which("node") or not shutil.which("git"):
            raise unittest.SkipTest("needs node and git")
        cls.tmp = Path(tempfile.mkdtemp())
        cls.repo = cls.tmp / "demo-repo"
        subprocess.run([sys.executable, "demo/build_demo_repo.py", str(cls.repo)], cwd=ROOT, check=True,
                       capture_output=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, onerror=lambda f, p, _: (Path(p).chmod(0o666), f(p)))

    def vaccinate(self, mutants):
        spec = json.loads((ROOT / mutants).read_text(encoding="utf-8"))
        results = run.run_mutants(spec["mutants"], self.repo, "npm test --silent", 120, log=lambda *_: None)
        return run.summarize("demo-repo", spec["antigens"], results)

    def test_miner_finds_the_three_fixes_and_the_postmortem(self):
        fixes = list(mine.fix_commits(self.repo))
        self.assertEqual(len(fixes), 3)
        self.assertEqual(mine.incident_docs(self.repo), ["docs/postmortems/2026-04-invoice-run-crash.md"])

    def test_baseline_immunity_is_two_of_six_and_repo_is_restored(self):
        s = self.vaccinate("examples/mutants.example.json")
        self.assertEqual((s["killed"], s["total"]), (2, 6))
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.repo,
                                capture_output=True, text=True).stdout
        self.assertEqual(status, "", "run.py must restore every mutated file")


if __name__ == "__main__":
    unittest.main()
