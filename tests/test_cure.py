"""Tests for curing (patch) and preventing (guard, Semgrep rules).  Run:  python -m unittest discover tests"""
import copy
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
import guard  # noqa: E402
import patch  # noqa: E402

KB = debug.learn([("invoice-kit", ROOT / "examples/mutants.example.json")])
NEW_CODE = (ROOT / "examples/debug-samples/new-feature.js").read_text(encoding="utf-8")
HAVE = {"git": bool(shutil.which("git")), "node": bool(shutil.which("node"))}


def rmtree(p):
    shutil.rmtree(p, onerror=lambda f, x, _: (Path(x).chmod(0o666), f(x)))


def demo_repo(tmp):
    repo = tmp / "r"
    subprocess.run([sys.executable, str(ROOT / "demo/build_demo_repo.py"), str(repo)], check=True, capture_output=True)
    return repo


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          capture_output=True, text=True, check=check)


class Template(unittest.TestCase):
    def test_dollar_groups_like_javascript(self):
        import re
        m = re.search(r"(a)(b)?", "a")
        self.assertEqual(patch.apply_template(m, "[$1|$2|$3]"), "[a||]")


class RecipeTemplates(unittest.TestCase):
    """Agents often write Python-style group references; they must work like $1."""

    def test_python_style_groups_are_accepted(self):
        self.assertEqual(patch.normalize_template(r"\1.\g<2>?.$3"), "$1.$2?.$3")
        kb = copy.deepcopy(KB)
        for a in kb["antigens"]:
            for p in a["signatures"].get("patches", []):
                p["replace"] = p["replace"].replace("$", "\\")     # $1 -> \1
        new, changes, _ = patch.patch_text(NEW_CODE, kb, "javascript")
        self.assertEqual(new, patch.patch_text(NEW_CODE, KB, "javascript")[0])
        self.assertEqual(len(changes), 3)

    def test_every_reference_recipe_fixes_its_own_example(self):
        for a in KB["antigens"]:
            with self.subTest(antigen=a["key"]):
                self.assertEqual(patch.check_recipes(a), [])

    def test_a_recipe_that_leaves_group_references_is_reported(self):
        a = copy.deepcopy(next(x for x in KB["antigens"] if x["id"] == "A41"))
        a["signatures"]["patches"][0]["replace"] = ".slice($7)"          # a group that doesn't exist -> ''
        self.assertEqual(patch.check_recipes(a), [])                      # expands to '' (JS behaviour), no leftovers
        a["signatures"]["patches"][0]["replace"] = ".slice(%1)"           # typo'd reference survives literally
        a["signatures"]["patches"][0]["regex"] = r"\.slice\(([^()]*?)\s*-\s*1\s*\)"
        self.assertEqual(patch.check_recipes(a), [])
        b = copy.deepcopy(a)
        b["signatures"]["patches"][0]["regex"] = r"will-never-match"
        self.assertTrue(any("doesn't change the example" in p for p in patch.check_recipes(b)))

    def test_learn_fails_loudly_on_a_broken_recipe(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            spec = json.loads((ROOT / "examples/mutants.example.json").read_text(encoding="utf-8"))
            spec["antigens"][0]["signatures"]["patches"][0]["regex"] = "will-never-match"
            f = tmp / "a.json"
            f.write_text(json.dumps(spec), encoding="utf-8")
            r = subprocess.run([sys.executable, str(ROOT / "bugvaccine.py"), "learn", "--source", f"x={f}",
                                "-o", str(tmp / "kb.json")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("RECIPE CHECK FAILED", r.stdout)
            self.assertTrue((tmp / "kb.json").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class PatchText(unittest.TestCase):
    def test_all_three_repeated_bugs_get_the_historical_fix(self):
        new, changes, unpatched = patch.patch_text(NEW_CODE, KB, "javascript")
        self.assertEqual([c["key"] for c in changes], ["invoice-kit:A41", "invoice-kit:A63", "invoice-kit:A57"])
        self.assertEqual(unpatched, [])
        self.assertIn("slice(from, from + perPage);", new)
        self.assertIn("Math.round(e.amount * 100), 0) / 100", new)
        self.assertIn("customer.profile?.firstName", new)
        code_hits = [r for m in debug.match(new, KB) for r in m["reasons"] if r["kind"] == "code"]
        self.assertEqual(code_hits, [], "patched code must no longer match any bug signature")

    def test_only_lines_matching_a_bug_signature_are_touched(self):
        text = "const a = xs.slice(1, n - 1); // intentionally drops the last item\nconst b = customer.name;\n"
        kb = copy.deepcopy(KB)
        for a in kb["antigens"]:
            a["signatures"]["code"] = [c for c in a["signatures"]["code"] if "slice" not in c["regex"]]
        new, changes, _ = patch.patch_text(text, kb, "javascript")
        self.assertEqual((new, changes), (text, []))

    def test_line_endings_and_untouched_lines_are_preserved(self):
        text = "// header\r\nreturn customer.address.city;\r\n// footer\r\n"
        new, changes, _ = patch.patch_text(text, KB, "javascript")
        self.assertEqual(new, "// header\r\nreturn customer.address?.city;\r\n// footer\r\n")
        self.assertEqual(len(changes), 1)

    def test_bug_without_a_recipe_is_reported_not_guessed(self):
        kb = copy.deepcopy(KB)
        for a in kb["antigens"]:
            a["signatures"].pop("patches", None)
        new, changes, unpatched = patch.patch_text(NEW_CODE, kb, "javascript")
        self.assertEqual((new, changes), (NEW_CODE, []))
        self.assertEqual(len(unpatched), 3)

    def test_learn_rejects_a_risky_patch_regex(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            f = tmp / "a.json"
            f.write_text(json.dumps({"antigens": [{"id": "Z", "title": "t", "pattern": "p", "signatures": {
                "code": [{"regex": "x", "explain": "e"}], "patches": [{"regex": "(a+)+$", "replace": "b"}]}}]}),
                encoding="utf-8")
            with self.assertRaises(ValueError):
                debug.learn([("x", f)])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(HAVE["git"] and HAVE["node"], "needs git and node")
class PatchFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.tmp)
        (self.repo / "src/loyalty.js").write_text(NEW_CODE, encoding="utf-8")

    def tearDown(self):
        rmtree(self.tmp)

    def test_apply_tests_and_verifies(self):
        r = patch.patch_files(self.repo, ["src/loyalty.js"], KB, apply=True, test_cmd="node --test")
        self.assertEqual((r["applied"], r["tests"], r["verified"]), (True, "pass", True))
        self.assertIn("customer.profile?.firstName", (self.repo / "src/loyalty.js").read_text(encoding="utf-8"))

    def test_dry_run_changes_nothing(self):
        r = patch.patch_files(self.repo, ["src/loyalty.js"], KB, apply=False)
        self.assertFalse(r["applied"])
        self.assertIn("+  return entries.slice(from, from + perPage);", r["files"][0]["diff"])
        self.assertEqual((self.repo / "src/loyalty.js").read_text(encoding="utf-8"), NEW_CODE)

    def test_a_patch_that_breaks_the_tests_is_rolled_back(self):
        # a test that loads loyalty.js, so a broken patch there makes the suite fail
        (self.repo / "test/loyalty.test.js").write_text(
            "import { test } from 'node:test';\nimport '../src/loyalty.js';\ntest('loads', () => {});\n", encoding="utf-8")
        kb = copy.deepcopy(KB)
        for a in kb["antigens"]:
            for p in a["signatures"].get("patches", []):
                p["replace"] = "SYNTAX ERROR ("        # a broken recipe
        before = {f: f.read_bytes() for f in (self.repo / "src").glob("*.js")}
        r = patch.patch_files(self.repo, ["src/loyalty.js"], kb, apply=True, test_cmd="node --test")
        self.assertTrue(r["rolled_back"])
        self.assertFalse(r["applied"])
        self.assertEqual({f: f.read_bytes() for f in (self.repo / "src").glob("*.js")}, before)

    def test_knowledge_files_and_docs_are_never_patched(self):
        # `patch --staged` right after `guard install` sees the staged knowledge base, whose
        # stored "before" examples are the bugs themselves: patching them would corrupt it
        kb_file = self.repo / ".bugvaccine/company-knowledge.json"
        kb_file.parent.mkdir(exist_ok=True)
        kb_file.write_text(json.dumps(KB, indent=2), encoding="utf-8")
        (self.repo / "docs/notes.md").write_text("return items.slice(start, start + size - 1);\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in (kb_file, self.repo / "docs/notes.md")}
        r = patch.patch_files(self.repo, [".bugvaccine/company-knowledge.json", "docs/notes.md", "src/loyalty.js"],
                              KB, apply=True, test_cmd="node --test")
        self.assertEqual([f["file"] for f in r["files"]], ["src/loyalty.js"])
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_files_outside_the_repo_are_refused(self):
        with self.assertRaises(ValueError):
            patch.patch_files(self.repo, ["../outside.js"], KB)


@unittest.skipUnless(HAVE["git"], "needs git")
class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.tmp)
        (self.repo / ".bugvaccine").mkdir()
        shutil.copy(ROOT / "examples/mutants.example.json", self.repo / ".bugvaccine/antigens.json")

    def tearDown(self):
        rmtree(self.tmp)

    def test_hook_blocks_a_commit_that_repeats_a_known_bug_and_allows_a_clean_one(self):
        guard.install(self.repo, ROOT / "bugvaccine.py")
        (self.repo / "src/paging2.js").write_text("export const f = (xs, n) => xs.slice(0, 0 + n - 1);\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        r = git(self.repo, "commit", "-m", "feat: paging", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("repeats bugs the company has already fixed", r.stdout + r.stderr)
        (self.repo / "src/paging2.js").write_text("export const f = (xs, n) => xs.slice(0, n);\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        self.assertEqual(git(self.repo, "commit", "-m", "feat: paging", check=False).returncode, 0)

    def test_install_refuses_when_there_is_no_knowledge_to_guard_with(self):
        (self.repo / ".bugvaccine/antigens.json").unlink()
        r = subprocess.run([sys.executable, str(ROOT / "bugvaccine.py"), "guard", "install", str(self.repo)],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No bug knowledge to guard with", r.stdout + r.stderr)
        self.assertFalse((guard.hooks_dir(self.repo) / "pre-commit").exists())

    def test_hook_uses_an_explicit_knowledge_base(self):
        kb = self.tmp / "kb.json"
        kb.write_text(json.dumps(KB), encoding="utf-8")
        (self.repo / ".bugvaccine/antigens.json").unlink()
        r = subprocess.run([sys.executable, str(ROOT / "bugvaccine.py"), "guard", "install", str(self.repo), "--kb", str(kb)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        (self.repo / "src/p.js").write_text("export const f = (xs, n) => xs.slice(0, 0 + n - 1);\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        self.assertNotEqual(git(self.repo, "commit", "-m", "x", check=False).returncode, 0)

    def test_install_refuses_to_overwrite_someone_elses_hook_and_uninstall_is_scoped(self):
        hook = guard.hooks_dir(self.repo) / "pre-commit"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("#!/bin/sh\necho team hook\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            guard.install(self.repo, ROOT / "bugvaccine.py")
        self.assertFalse(guard.uninstall(self.repo))
        self.assertIn("team hook", hook.read_text(encoding="utf-8"))


class DiffScope(unittest.TestCase):
    def test_knowledge_files_docs_and_json_are_not_reviewed(self):
        bad = "+  return items.slice(start, start + size - 1);\n"
        diff = "".join(f"diff --git a/{p} b/{p}\n--- a/{p}\n+++ b/{p}\n@@ -0,0 +1 @@\n{bad}"
                       for p in [".bugvaccine/antigens.json", "docs/notes.md", "data.json", "src/real.js"])
        self.assertEqual([f["file"] for f in debug.match_diff(diff, KB)], ["src/real.js"])


class SemgrepRules(unittest.TestCase):
    def test_one_rule_per_code_signature_with_intact_regexes(self):
        text, count = guard.semgrep_rules(KB)
        expected = sum(len(a["signatures"].get("code", [])) for a in KB["antigens"])
        self.assertEqual(count, expected)
        self.assertEqual(text.count("  - id: bug-vaccine-"), expected)
        regexes = [json.loads(l.split("pattern-regex: ", 1)[1]) for l in text.splitlines() if "pattern-regex:" in l]
        self.assertEqual(regexes, [c["regex"] for a in KB["antigens"] for c in a["signatures"].get("code", [])])


if __name__ == "__main__":
    unittest.main()
