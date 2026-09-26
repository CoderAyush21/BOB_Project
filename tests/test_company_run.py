"""Regression tests for the problems found by running Bug Vaccine as a company ("Acme Corp").
Run:  python -m unittest discover tests"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vaccine"))

import rag  # noqa: E402
import run  # noqa: E402

BV = [sys.executable, str(ROOT / "bugvaccine.py")]
HAVE_TOOLS = bool(shutil.which("node") and shutil.which("git"))


def rmtree(p):
    shutil.rmtree(p, onerror=lambda f, x, _: (Path(x).chmod(0o666), f(x)))


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


@unittest.skipUnless(HAVE_TOOLS, "needs node and git")
class CompanyWorkspace(unittest.TestCase):
    """One workspace whose path contains a space, like 'Acme Corp'."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()) / "Acme Corp"
        cls.repo = cls.tmp / "invoice-kit"
        subprocess.run([sys.executable, str(ROOT / "demo/build_demo_repo.py"), str(cls.repo)], check=True, capture_output=True)
        r = subprocess.run(BV + ["init", str(cls.repo), "--test", "npm test --silent"], capture_output=True, text=True)
        cls.init_out = r.stdout
        shutil.copy(ROOT / "examples/mutants.example.json", cls.repo / ".bugvaccine/mutants.json")
        git(cls.repo, "add", "-A")
        git(cls.repo, "commit", "-qm", "add bug vaccine")

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.tmp.parent)

    def run_bv(self, *args, cwd=None):
        return subprocess.run(BV + list(args), capture_output=True, text=True, cwd=cwd)

    # finding 1: a new file that repeats known bugs must never get a green PR comment
    def test_pr_comment_flags_known_bugs_in_a_brand_new_file(self):
        git(self.repo, "checkout", "-qb", "feature/loyalty")
        try:
            shutil.copy(ROOT / "examples/debug-samples/new-feature.js", self.repo / "src/loyalty.js")
            git(self.repo, "add", "-A")
            git(self.repo, "commit", "-qm", "feat: loyalty")
            r = self.run_bv("pr", str(self.repo), "--base", "main")
            comment = (self.repo / ".bugvaccine/pr-comment.md").read_text(encoding="utf-8")
            self.assertNotIn("✅", comment, comment)
            self.assertIn("⚠️ 3 past bugs could come back", comment)
            for line in (":5`", ":9`", ":13`"):
                self.assertIn("src/loyalty.js" + line, comment)
            r = self.run_bv("pr", str(self.repo), "--base", "main", "--fail-on-new-risks")
            self.assertEqual(r.returncode, 2)
        finally:
            git(self.repo, "checkout", "-q", "main")

    # finding 3: the committed prompt must not contain this machine's absolute path or username
    def test_committed_prompt_has_no_absolute_path(self):
        prompt = (self.repo / ".bugvaccine/PROMPT.md").read_text(encoding="utf-8")
        line = next(l for l in prompt.splitlines() if "Bug Vaccine command is" in l)
        self.assertNotIn(str(ROOT), line)
        self.assertNotIn(str(Path.home()), line)
        self.assertRegex(line, r"python (\.\./)+.*bugvaccine\.py")

    # finding 6: generated dashboards are git-ignored
    def test_dashboard_is_git_ignored(self):
        self.assertIn("dashboard*.html", (self.repo / ".bugvaccine/.gitignore").read_text(encoding="utf-8"))

    # finding 9: printed next steps are quoted and runnable from where the user is
    def test_init_next_steps_quote_paths_with_spaces(self):
        self.assertIn(f'"{self.repo}"', self.init_out)
        self.assertNotIn("run `python bugvaccine.py", self.init_out)

    # finding 5: --compare accepts the bare file name from the guide
    def test_compare_accepts_a_name_inside_bugvaccine(self):
        self.run_bv("run", str(self.repo), "-o", "results-before.json")
        r = self.run_bv("run", str(self.repo), "--html", "-o", "results-after.json", "--compare", "results-before.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.repo / ".bugvaccine/results-before.json").exists())
        self.assertTrue((self.repo / ".bugvaccine/results-after.json").exists())


@unittest.skipUnless(HAVE_TOOLS, "needs node and git")
class InitFailure(unittest.TestCase):
    # finding 4: init shows why the test command failed
    def test_init_shows_the_test_output(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            repo = tmp / "r"
            subprocess.run([sys.executable, str(ROOT / "demo/build_demo_repo.py"), str(repo)], check=True, capture_output=True)
            r = subprocess.run(BV + ["init", str(repo), "--test", 'python -c "raise SystemExit(\'boom-marker\')"'],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("boom-marker", r.stdout)
            self.assertIn("--force", r.stdout)
        finally:
            rmtree(tmp)


class Encoding(unittest.TestCase):
    # finding 2: a Latin-1 source file is mutated and restored byte-for-byte instead of crashing the run
    def test_latin1_file_is_mutated_and_restored_exactly(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "src").mkdir()
            original = "// Caf\xe9 pricing\nexport const vat = (x) => x * 0.2;\n".encode("latin-1")
            f = tmp / "src/legacy.js"
            f.write_bytes(original)
            mutants = [{"id": "L1", "antigen": "A", "file": "src/legacy.js", "find": "x * 0.2", "replace": "x * 0.21"}]
            check = 'python -c "import sys; d=open(\'src/legacy.js\',\'rb\').read(); sys.exit(0 if b\'0.21\' in d and b\'\\xe9\' in d else 1)"'
            res = run.run_mutants(mutants, tmp, check, 60, log=lambda *_: None)
            self.assertEqual(res[0]["status"], "survived")    # tests saw the mutated Latin-1 file
            self.assertEqual(f.read_bytes(), original)        # and it was restored exactly
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(shutil.which("git"), "needs git")
class Naming(unittest.TestCase):
    # finding 7: two repos with the same folder name must not silently merge
    def test_duplicate_project_names_are_refused_and_name_path_works(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            for org in ("a", "b"):
                d = tmp / org / "invoice-kit" / ".bugvaccine"
                d.mkdir(parents=True)
                shutil.copy(ROOT / "examples/mutants.example.json", d / "antigens.json")
            a, b = tmp / "a/invoice-kit", tmp / "b/invoice-kit"
            r = subprocess.run(BV + ["learn", str(a), str(b), "-o", str(tmp / "kb.json")], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("both called 'invoice-kit'", r.stdout + r.stderr)
            r = subprocess.run(BV + ["learn", f"billing={a}", f"payments={b}", "-o", str(tmp / "kb.json")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            names = {s["name"] for s in json.loads((tmp / "kb.json").read_text(encoding="utf-8"))["sources"]}
            self.assertEqual(names, {"billing", "payments"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class RagNoise(unittest.TestCase):
    # finding 11: non-bug commits are kept out of the RAG index
    def test_noise_filter(self):
        for s in ["Fix mypy errors", "Fix GitHub Actions badge", "[pre-commit.ci] pre-commit autoupdate",
                  "Speed up string parsing (#28)", "Add pypy to CI test matrix (#89)"]:
            self.assertTrue(rag.is_noise(s), s)
        for s in ["FIX: Raise an error for duplicate keys in inline tables",
                  "fix: crash when customer has no address (#57)", "Limit number of parts of a key (#286)"]:
            self.assertFalse(rag.is_noise(s), s)

    def test_duplicate_patterns_are_indexed_once(self):
        c = {"kind": "pattern", "repo": "x", "ref": "x:A1", "title": "t", "text": "t"}
        self.assertEqual(len(rag.build_index([dict(c), dict(c)])["chunks"]), 1)


class Summary(unittest.TestCase):
    # finding 12: "0/0 (0%)" is not printed when nothing applies
    def test_no_mutants_message(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run.print_summary(run.summarize("r", [], []), "x.json")
        self.assertIn("No stored mutants apply", buf.getvalue())
        self.assertNotIn("0/0", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
