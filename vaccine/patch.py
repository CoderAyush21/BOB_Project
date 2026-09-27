"""Cure: apply the fix your team already wrote to new code that repeats a known bug.

A bug pattern's signature can carry fix recipes (written by Bob from the original fix commit):
    "patches": [{"regex": "...", "replace": "... $1 ...", "explain": "..."}]
Replacement templates use $1..$9 (JavaScript's syntax); the dashboard runs the same recipes.

Safety rules:
  - a recipe is applied only on a line where that same bug's code signature matched;
  - nothing is written unless apply=True, and only to files inside the repo;
  - after writing, the test command must still pass, otherwise every file is restored;
  - each patched file is re-scanned, and a patch only counts if the signature no longer matches.
Lines that match a bug with no recipe are reported as "needs a human or Bob".
"""
import difflib
import re
from pathlib import Path

import debug
import run

_TEMPLATE = re.compile(r"\$(\d)")
_PY_GROUP = re.compile(r"\\g<(\d)>|\\(\d)")


def normalize_template(template):
    """Accept Python-style group references too: \\1 and \\g<1> become $1 (what the engines expand)."""
    return _PY_GROUP.sub(lambda t: "$" + (t.group(1) or t.group(2)), template)


def apply_template(m, template):
    """Expand $1..$9 like JavaScript's String.replace (a missing group becomes '')."""
    return _TEMPLATE.sub(lambda t: m.group(int(t.group(1))) or "" if int(t.group(1)) <= (m.re.groups or 0) else "",
                         normalize_template(template))


def check_recipes(antigen):
    """Apply an antigen's recipes to its own example.before. Returns a list of problems (empty = fine)."""
    s = antigen.get("signatures", {})
    ex, patches = s.get("example") or {}, s.get("patches") or []
    if not patches:
        return []
    if not ex.get("before"):
        return ["has fix recipes but no example.before to check them against"]
    kb = {"antigens": [{**antigen, "key": antigen.get("key", antigen.get("id"))}]}
    problems = []
    for line in ex["before"].splitlines():
        new, changes, unpatched = patch_text(line, kb, s.get("lang"))
        if unpatched:
            problems.append(f"recipe doesn't change the example line: {line.strip()}")
        for c in changes:
            if _TEMPLATE.search(c["after"]) or _PY_GROUP.search(c["after"]):
                problems.append(f"recipe output still contains a group reference: {c['after']}")
    return problems


def _applies(sig, lang):
    return not (lang and sig.get("lang") and sig["lang"] != lang)


def patch_text(text, kb, lang=None):
    """Return (patched_text, changes, unpatched). Line endings are preserved."""
    lang = lang or debug.detect_lang(text)
    out, changes, unpatched = [], [], []
    for n, raw in enumerate(text[:debug.MAX_TEXT].splitlines(keepends=True), 1):
        body = raw.rstrip("\r\n")
        ending = raw[len(body):]
        line = body[:debug.MAX_LINE]
        new = line
        for a in kb["antigens"]:
            s = a.get("signatures", {})
            if not _applies(s, lang):
                continue
            if not any(re.search(c["regex"], new) for c in s.get("code", [])):
                continue
            before = new
            for p in s.get("patches", []):
                new = re.sub(p["regex"], lambda m, t=p["replace"]: apply_template(m, t), new)
            if new != before:
                changes.append({"line": n, "before": before.strip(), "after": new.strip(), "key": a["key"],
                                "title": a.get("title", a["key"]),
                                "explain": next((p.get("explain", "") for p in s.get("patches", [])), "")})
            else:
                unpatched.append({"line": n, "text": before.strip(), "key": a["key"], "title": a.get("title", a["key"]),
                                  "fix_hint": s.get("fix_hint", "")})
        out.append(new + body[len(line):] + ending)
    return "".join(out) + text[debug.MAX_TEXT:], changes, unpatched


def unified_diff(path, before, after):
    return "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                        fromfile=f"a/{path}", tofile=f"b/{path}"))


def patch_files(repo, files, kb, apply=False, test_cmd=None, timeout=120):
    """Patch files (repo-relative paths). Returns a report dict; see module docstring for the rules."""
    repo = Path(repo)
    report = {"files": [], "applied": False, "tests": None, "rolled_back": False, "verified": None}
    originals = {}
    for rel in files:
        path = run.safe_path(repo, rel)
        if not path.is_file():
            continue
        text, encoding = run.read_source(path)
        lang = debug.EXT_LANG.get(path.suffix.lower())
        new, changes, unpatched = patch_text(text, kb, lang)
        if changes or unpatched:
            report["files"].append({"file": rel, "encoding": encoding, "changes": changes, "unpatched": unpatched,
                                    "diff": unified_diff(rel, text, new) if changes else "", "_new": new})
        if changes:
            originals[path] = path.read_bytes()
    if not apply or not originals:
        return _clean(report)

    for f in report["files"]:
        if f["changes"]:
            path = run.safe_path(repo, f["file"])
            path.write_bytes(f["_new"].encode(f["encoding"]))
    report["applied"] = True
    if test_cmd:
        code, _, output = run.run_tests(repo, test_cmd, timeout, with_output=True)
        report["tests"] = "pass" if code == 0 else "fail"
        if code != 0:
            for path, data in originals.items():
                path.write_bytes(data)
            report.update(applied=False, rolled_back=True, test_output=output)
            return _clean(report)
    # verify: the patched bugs' signatures must no longer match the patched lines
    still = []
    for f in report["files"]:
        if not f["changes"]:
            continue
        text, _ = run.read_source(run.safe_path(repo, f["file"]))
        lines = text.splitlines()
        for c in f["changes"]:
            a = next(x for x in kb["antigens"] if x["key"] == c["key"])
            if any(re.search(s["regex"], lines[c["line"] - 1]) for s in a["signatures"].get("code", [])):
                still.append(f"{f['file']}:{c['line']}")
    report["verified"] = not still
    report["still_matching"] = still
    return _clean(report)


def _clean(report):
    for f in report["files"]:
        f.pop("_new", None)
    return report
