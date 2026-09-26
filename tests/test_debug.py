"""Tests for the company-knowledge debugger.  Run:  python -m unittest discover tests"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vaccine"))

import debug  # noqa: E402

KB = debug.learn([("invoice-kit", ROOT / "examples/mutants.example.json"),
                  ("tomli", ROOT / "case-studies/tomli/mutants.json")])
DEMO_SRC = r"""
export function page(items, pageNo, size) {
  const start = pageNo * size;
  return items.slice(start, start + size);
}
export function billingCity(customer) {
  return customer.address?.city ?? 'Unknown';
}
export function invoiceTotal(lines) {
  const cents = lines.reduce((sum, l) => sum + Math.round(l.price * 100) * l.qty, 0);
  return cents / 100;
}
"""


def keys(matches, confidence="known bug"):
    return [m["key"] for m in matches if m["confidence"] == confidence]


class Learn(unittest.TestCase):
    def test_merges_sources_with_repo_prefixed_keys(self):
        self.assertEqual(len(KB["antigens"]), 9)
        self.assertIn("tomli:T4", {a["key"] for a in KB["antigens"]})
        self.assertEqual({s["name"]: s["with_signatures"] for s in KB["sources"]}, {"invoice-kit": 3, "tomli": 3})

    def test_every_signature_regex_is_javascript_compatible(self):
        # the dashboard runs these in the browser; Python-only syntax would silently break it
        for a in KB["antigens"]:
            for pat in debug.signature_regexes(a):
                with self.subTest(key=a["key"], pat=pat):
                    self.assertNotRegex(pat, r"\(\?P<|\(\?[aiLmsux]+\)|\\A|\\Z")
                    re.compile(pat)


class Match(unittest.TestCase):
    def test_js_crash_matches_the_null_guard_incident(self):
        m = debug.match("TypeError: Cannot read properties of undefined (reading 'email')", KB)
        self.assertEqual(keys(m)[0], "invoice-kit:A57")

    def test_python_traceback_matches_tomli_unicode_bug(self):
        text = (ROOT / "examples/debug-samples/python-traceback.txt").read_text(encoding="utf-8")
        self.assertEqual(keys(debug.match(text, KB))[0], "tomli:T4")

    def test_scan_finds_all_three_repeated_bugs_in_new_code(self):
        text = (ROOT / "examples/debug-samples/new-feature.js").read_text(encoding="utf-8")
        found = {m["key"] for m in debug.match(text, KB) if any(r["kind"] == "code" for r in m["reasons"])}
        self.assertEqual(found, {"invoice-kit:A41", "invoice-kit:A57", "invoice-kit:A63"})

    def test_fixed_code_raises_no_code_alarms(self):
        code_hits = [m for m in debug.match(DEMO_SRC, KB) if any(r["kind"] == "code" for r in m["reasons"])]
        self.assertEqual(code_hits, [])

    def test_no_signature_fires_on_any_file_of_the_fixed_demo_repo(self):
        # every source file of the demo, as it is after all three fixes, must be clean
        import subprocess, tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        try:
            subprocess.run([sys.executable, str(ROOT / "demo/build_demo_repo.py"), str(tmp / "r")], check=True, capture_output=True)
            for f in sorted((tmp / "r/src").glob("*.js")):
                with self.subTest(file=f.name):
                    hits = [r for m in debug.match(f.read_text(encoding="utf-8"), KB) for r in m["reasons"] if r["kind"] == "code"]
                    self.assertEqual(hits, [], f"false positive in fixed {f.name}")
        finally:
            shutil.rmtree(tmp, onerror=lambda fn, p, _: (Path(p).chmod(0o666), fn(p)))

    def test_code_signatures_respect_language(self):
        # a Python-only signature (chr) must not fire on JavaScript
        m = debug.match("const s = String.fromCharCode(x); function chr(x) { return chr(x) }", KB, lang="javascript")
        self.assertNotIn("tomli:T4", keys(m))

    def test_unknown_problem_matches_nothing_strongly(self):
        self.assertEqual(keys(debug.match("Login button does nothing on Safari", KB)), [])

    def test_diff_review_flags_only_added_lines_with_new_line_numbers(self):
        diff = (ROOT / "examples/debug-samples/pr-88.diff").read_text(encoding="utf-8")
        found = [(f["file"], f["line"], f["key"]) for f in debug.match_diff(diff, KB)]
        # float sum on line 3 and missing null guard on line 7 of the new file; the correct pageOf() and the
        # REMOVED buggy slice in paginate.js must not be flagged
        self.assertEqual(found, [("src/refunds.js", 3, "invoice-kit:A63"), ("src/refunds.js", 7, "invoice-kit:A57")])

    def test_is_diff(self):
        self.assertTrue(debug.is_diff("diff --git a/x b/x\n"))
        self.assertTrue(debug.is_diff("@@ -1,2 +1,3 @@\n+x"))
        self.assertFalse(debug.is_diff("TypeError: boom"))

    def test_bob_prompt_includes_known_fix(self):
        text = "invoice totals are off by a cent"
        prompt = debug.bob_prompt(text, debug.match(text, KB))
        self.assertIn("Float money math", prompt)
        self.assertIn("integer cents", prompt)


if __name__ == "__main__":
    unittest.main()
