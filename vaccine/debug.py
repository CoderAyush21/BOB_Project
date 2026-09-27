"""Debug with company knowledge: match errors, bug reports and code against
bugs your company has already had.

"Training" = teaching it your bug patterns. For each repo, Bob writes a
`signatures` block for each antigen (see bob-prompts/your-repo/PROMPT.md):
    {"lang": "javascript" | "python" | ...,
     "code":   [{"regex": ..., "explain": ...}],   matched line by line, case-sensitive
     "errors": [regex, ...],                        matched against the whole text, case-insensitive
     "fix_hint": ..., "example": {"before", "after"}, "antibody": ...}
`learn` merges every repo's antigens into one knowledge base.

Regexes must work in both Python and JavaScript (the dashboard runs the same
matching in the browser): avoid (?P<name>), possessive quantifiers and inline flags.

This finds KNOWN bug patterns only. For anything it doesn't recognise, use
`--prompt` to hand the problem to Bob together with the matched knowledge.
"""
import argparse
import datetime as dt
import glob
import json
import re
import sys
from pathlib import Path

from redact import redact_text

ERROR_WEIGHT, CODE_WEIGHT, KEYWORD_WEIGHT = 5, 3, 1
MAX_TEXT, MAX_LINE = 200_000, 2_000   # bound the work any regex can do on pasted input
# A group that contains a quantifier and is itself quantified, e.g. (a+)+ or (\w+\s?)*:
# the classic catastrophic-backtracking shape. Rejected at learn time and in the dashboard.
_NESTED_QUANTIFIER = re.compile(r"(?<!\\)\((?:\\.|\[(?:\\.|[^\]])*\]|[^()\\])*[+*](?:\\.|\[(?:\\.|[^\]])*\]|[^()\\])*\)[+*{]")


def risky_regex(pattern):
    return bool(_NESTED_QUANTIFIER.search(pattern))
STOP = set("""the and for with that this from into when then than have has was were are not but you your our
their them they its it's any all can could would should will does did done been being also only just more most
other some such each every very what which while where there here about after before over under again""".split())


# ── knowledge base ─────────────────────────────────────────────────────────

def load_antigens(path):
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    return spec["antigens"] if isinstance(spec, dict) else spec


def learn(sources):
    """sources: list of (name, path to antigens.json or mutants.json). Returns a knowledge base dict."""
    kb, summary = [], []
    for name, path in sources:
        antigens = load_antigens(path)
        for a in antigens:
            kb.append({**a, "repo": name, "key": f"{name}:{a['id']}"})
        summary.append({"name": name, "antigens": len(antigens),
                        "with_signatures": sum("signatures" in a for a in antigens)})
    for a in kb:  # fail early on a regex that won't compile or could hang the matcher
        for pat in signature_regexes(a):
            re.compile(pat)
            if risky_regex(pat):
                raise ValueError(f"{a['key']}: regex {pat!r} has a nested quantifier and could hang on "
                                 f"some inputs (catastrophic backtracking). Rewrite it without (x+)+ style groups.")
    return {"version": 1, "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "sources": summary, "antigens": kb}


def signature_regexes(a):
    s = a.get("signatures", {})
    return ([c["regex"] for c in s.get("code", [])] + list(s.get("errors", []))
            + [p["regex"] for p in s.get("patches", [])])


# ── matching ───────────────────────────────────────────────────────────────

def detect_lang(text):
    if re.search(r"Traceback \(most recent call last\)|^\s*def \w+\(|^\s*import \w+$|\bself\.", text, re.M):
        return "python"
    if re.search(r"=>|\bconst \w+|\bfunction\b|\bexport \w+|at \w+ \(.*\.[jt]s:\d+", text):
        return "javascript"
    return None


def words(text):
    return {w for w in re.findall(r"[a-z][a-z0-9_]{3,}", text.lower()) if w not in STOP}


def match(text, kb, lang=None):
    """Rank known bug patterns that match `text` (an error, stack trace, bug report or code)."""
    text = text[:MAX_TEXT]
    lang = lang or detect_lang(text)
    lines = [line[:MAX_LINE] for line in text.splitlines()]
    text_words = words(text)
    out = []
    for a in kb["antigens"]:
        s = a.get("signatures", {})
        reasons, score = [], 0
        for pat in s.get("errors", []):
            m = re.search(pat, text, re.I | re.M)
            snippet = m.group(0).strip().splitlines()[-1].strip()[:160] if m else None  # a traceback's key line
            if m and not any(r["text"] == snippet for r in reasons):
                score += ERROR_WEIGHT
                reasons.append({"kind": "error", "text": snippet})
        if not lang or not s.get("lang") or s.get("lang") == lang:
            for c in s.get("code", []):
                for i, line in enumerate(lines, 1):
                    if re.search(c["regex"], line):
                        score += CODE_WEIGHT
                        reasons.append({"kind": "code", "line": i, "text": line.strip()[:160], "explain": c["explain"]})
        shared = text_words & words(f"{a.get('title', '')} {a.get('pattern', '')}")
        if shared and (score or len(shared) >= 2):  # one shared word alone is noise
            score += KEYWORD_WEIGHT * min(len(shared), 3)
            reasons.append({"kind": "keywords", "text": ", ".join(sorted(shared)[:6])})
        if score:
            confidence = "known bug" if score >= CODE_WEIGHT else "possibly related"
            out.append({"key": a["key"], "score": score, "confidence": confidence, "reasons": reasons, "antigen": a})
    return sorted(out, key=lambda r: -r["score"])


EXT_LANG = {".py": "python", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
            ".ts": "javascript", ".tsx": "javascript", ".java": "java", ".go": "go"}


# Diff review only looks at source code. Docs, JSON (including Bug Vaccine's own knowledge files,
# whose example "before" lines are bugs on purpose) and other data files are skipped.
CODE_EXT = set(EXT_LANG) | {".rb", ".php", ".cs", ".kt", ".rs", ".c", ".h", ".cpp", ".hpp", ".swift", ".scala", ".vue", ".svelte"}


def is_code_file(path):
    p = Path(path)
    return p.suffix.lower() in CODE_EXT and ".bugvaccine" not in p.parts


def is_diff(text):
    return bool(re.search(r"^(diff --git |@@ -\d+(,\d+)? \+\d+(,\d+)? @@)", text, re.M))


def parse_diff(text):
    """Unified diff -> {file: [(new_line_number, added_line_text), ...]} (only added lines)."""
    files, cur, n = {}, None, 0
    for line in text[:MAX_TEXT].splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            cur = None if path == "/dev/null" else re.sub(r"^b/", "", path)
            if cur:
                files.setdefault(cur, [])
        elif line.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            n = int(m.group(1)) if m else 0
        elif cur is None or line.startswith("--- ") or line.startswith("diff --git"):
            continue
        elif line.startswith("+"):
            files[cur].append((n, line[1:]))
            n += 1
        elif not line.startswith("-") and not line.startswith("\\"):
            n += 1
    return files


def match_diff(text, kb):
    """Check only the lines a diff ADDS against code signatures. Returns [{file, line, text, explain, antigen}]."""
    findings = []
    for path, added in parse_diff(text).items():
        if not is_code_file(path):
            continue
        lang = EXT_LANG.get(Path(path).suffix.lower())
        for a in kb["antigens"]:
            s = a.get("signatures", {})
            if lang and s.get("lang") and s["lang"] != lang:
                continue
            for c in s.get("code", []):
                for n, line in added:
                    if re.search(c["regex"], line[:MAX_LINE]):
                        findings.append({"file": path, "line": n, "text": line.strip()[:160],
                                         "explain": c["explain"], "key": a["key"], "antigen": a})
    return sorted(findings, key=lambda f: (f["file"], f["line"]))


def bob_prompt(text, matches, sources=None):
    """Prompt for Bob. `sources` are RAG results (rag.search) to cite; secrets are redacted."""
    text = redact_text(text)
    known = [m for m in matches if m["confidence"] == "known bug"][:3]
    ctx = "\n".join(
        f"- {m['antigen'].get('title')} (from {m['antigen']['repo']}, fixed in: {m['antigen'].get('source_commit', '?')}). "
        f"Pattern: {m['antigen'].get('pattern', '')}. Known fix: {m['antigen'].get('signatures', {}).get('fix_hint', 'n/a')}"
        for m in known) or "- No known company bug pattern matched. Treat this as a new bug."
    src = ""
    if sources:
        src = "\n## Retrieved company sources (cite them as [1], [2], ...)\n" + "\n\n".join(
            f"[{i}] {s['chunk']['title']} ({s['chunk']['kind']}, {s['chunk']['ref']})\n{redact_text(s['chunk']['text'])[:900]}"
            for i, s in enumerate(sources, 1)) + "\n"
    return f"""You are debugging an issue at our company. Use our bug history first.

## The problem
```
{text.strip()[:4000]}
```

## Matching bugs we have already had (from Bug Vaccine's company knowledge base)
{ctx}
{src}
## What to do
0. Ground your answer in the sources above and cite them like [2]. If they don't cover the problem, say so plainly instead of guessing.
1. Check whether this is one of the known bugs above. If it is, point to the exact line and apply the known fix.
2. If it isn't, find the root cause yourself. Explain it in 2-3 sentences before changing anything.
3. Write a regression test that fails before the fix and passes after, and guard the *pattern*, not just this input.
4. If this is a new kind of bug, write a Bug Vaccine antigen for it (id, title, pattern, and a `signatures` block with
   `code` and `errors` regexes that work in both Python and JavaScript), so the company knowledge base learns it.
"""


# ── CLI ────────────────────────────────────────────────────────────────────

def print_matches(matches):
    if not matches:
        print("No known company bug pattern matches. Use --prompt to hand this to Bob as a new bug.")
        return
    for m in matches:
        a = m["antigen"]
        print(f"\n[{m['confidence'].upper()}] {a.get('title')}   ({a['repo']}, score {m['score']})")
        for r in m["reasons"]:
            where = f"line {r['line']}: " if r["kind"] == "code" else ""
            extra = f"  <- {r['explain']}" if r["kind"] == "code" else ""
            print(f"   {r['kind']:<8} {where}{r['text']}{extra}")
        sig = a.get("signatures", {})
        if sig.get("fix_hint"):
            print(f"   fix      {sig['fix_hint']}")
        if a.get("postmortem"):
            print(f"   incident {a['postmortem']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kb", default="knowledge.json", help="knowledge base built by `learn`")
    ap.add_argument("--error", help="error message, stack trace or bug report text")
    ap.add_argument("--error-file", help="read the error/report from a file")
    ap.add_argument("--scan", nargs="*", default=[], help="source files to scan for known risky patterns")
    ap.add_argument("--diff", help="unified diff file to review (only added lines are checked); '-' reads stdin")
    ap.add_argument("--prompt", action="store_true", help="also print a Bob debugging prompt")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    kb = json.loads(Path(args.kb).read_text(encoding="utf-8"))
    if args.diff:
        diff_text = sys.stdin.read() if args.diff == "-" else Path(args.diff).read_text(encoding="utf-8")
        findings = match_diff(diff_text, kb)
        if args.json:
            print(json.dumps([{k: v for k, v in f.items() if k != "antigen"} for f in findings], indent=2))
            return
        if not findings:
            print("No known company bug patterns in the lines this diff adds.")
        for f in findings:
            a = f["antigen"]
            print(f"{f['file']}:{f['line']}  {a.get('title')}  ({a['repo']})\n    {f['text']}\n    <- {f['explain']}")
            if a.get("signatures", {}).get("fix_hint"):
                print(f"    fix: {a['signatures']['fix_hint']}")
        sys.exit(1 if findings else 0)
    text = args.error or (Path(args.error_file).read_text(encoding="utf-8") if args.error_file else "")
    results = {}
    if text:
        results["error"] = match(text, kb)
    # expand patterns ourselves: PowerShell and cmd don't expand *.js for native commands
    scan = [x for f in args.scan for x in (sorted(glob.glob(f)) or [f])]
    for f in scan:
        results[f] = [m for m in match(Path(f).read_text(encoding="utf-8", errors="replace"), kb)
                      if any(r["kind"] == "code" for r in m["reasons"])]
    if not results:
        sys.exit("Give --error, --error-file or --scan.")
    if args.json:
        print(json.dumps(results, indent=2))
        return
    for name, matches in results.items():
        print(f"\n=== {'your error / report' if name == 'error' else name}")
        print_matches(matches)
    if args.prompt:
        print("\n" + "=" * 72 + "\nBOB PROMPT (paste into IBM Bob, in the affected repo)\n" + "=" * 72)
        print(bob_prompt(text or "\n".join(Path(f).read_text(encoding="utf-8") for f in args.scan),
                         results.get("error") or sum(results.values(), [])))


if __name__ == "__main__":
    main()
