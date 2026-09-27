"""Re-inject historical bug patterns (mutants) and check whether the tests catch them.

Usage:
    python vaccine/run.py mutants.json --repo demo-repo -o results.json --html report.html
    python vaccine/run.py mutants.json --repo demo-repo --compare results-before.json --html report.html
    python vaccine/run.py mutants.json --repo demo-repo --changed-since main --markdown pr-comment.md

For each mutant: apply one exact text replacement, run the test command,
restore the file.
  tests fail      -> KILLED   (caught: the codebase is immune to this bug)
  tests pass      -> SURVIVED (this old bug could come back unnoticed)
  tests time out  -> TIMEOUT  (counted as caught, as in standard mutation
                               testing, but reported separately so it's visible)

The test command runs through the shell (so `npm test`, `pytest -q` etc. work).
Only point --test at commands you trust.
Standard library only.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from redact import redact_text

CAUGHT = ("killed", "timeout")


# ── core ────────────────────────────────────────────────────────────────────

def apply_mutant(text, find, replace):
    """Return (mutated_text, hits). mutated_text is None unless `find` occurs exactly once.

    Mutants are written with LF line breaks. If the file uses CRLF (common on
    Windows checkouts), the find/replace strings are converted to match.
    """
    if "\r\n" in text:
        find, replace = find.replace("\r\n", "\n").replace("\n", "\r\n"), replace.replace("\r\n", "\n").replace("\n", "\r\n")
    hits = text.count(find)
    return (text.replace(find, replace) if hits == 1 else None), hits


def safe_path(repo, rel):
    """Resolve a mutant's file inside the repo. Raises ValueError for absolute paths, '..' escapes
    and symlinks that point outside the repository, so a malicious mutants.json can't write elsewhere."""
    if not rel or Path(rel).is_absolute() or Path(rel).drive:
        raise ValueError(f"'{rel}' is outside the repository (absolute paths are not allowed)")
    root = Path(repo).resolve()
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"'{rel}' is outside the repository")
    return target


def classify(returncode):
    if returncode == "timeout":
        return "timeout"
    return "survived" if returncode == 0 else "killed"


def run_tests(repo, cmd, timeout, with_output=False):
    """Run the test command. Returns (code, seconds), or (code, seconds, output_tail) with with_output."""
    # Python caches bytecode keyed on source mtime+size; a same-size mutant written
    # within the same second could otherwise be served stale. Never write caches.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=repo, shell=True, capture_output=True, text=True, timeout=timeout, env=env,
                           encoding="utf-8", errors="replace")
        code, out = p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = "timeout", f"(no result after {timeout}s)"
    secs = time.time() - t
    return (code, secs, tail(out)) if with_output else (code, secs)


def tail(text, lines=15):
    return "\n".join(text.strip().splitlines()[-lines:])


def explain_failure(output):
    """Turn common environment problems into a one-line hint."""
    if os.name == "nt" and re.search(r"(FileNotFoundError|No such file|Filename too long)", output) and \
            re.search(r"[A-Za-z]:\\[^\n]{200,}", output):
        return ("Hint: Windows paths over 260 characters can't be opened. Move the repo to a shorter path, "
                "or enable long paths (git config --global core.longpaths true, plus the LongPathsEnabled "
                "Windows setting).")
    if re.search(r"is not recognized as an internal or external command|command not found", output):
        return "Hint: the test command wasn't found. Check it runs on its own in this folder."
    return ""


def read_source(path):
    """Read a source file as (text, encoding). Falls back to Latin-1, which maps every byte to one
    character and back, so legacy-encoded files are mutated and restored byte-for-byte."""
    data = path.read_bytes()
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def changed_files(repo, base):
    out = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], cwd=repo,
                         check=True, capture_output=True, text=True).stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def run_mutants(mutants, repo, test_cmd, timeout, log=print):
    results = []
    for m in mutants:
        try:
            path = safe_path(repo, m["file"])
            if not path.is_file():
                raise ValueError(f"'{m['file']}' not found")
        except ValueError as e:
            results.append({**m, "status": "invalid", "detail": str(e)})
            log(f"  {m['id']:<5} INVALID   ({e})")
            continue
        original = path.read_bytes()
        text, encoding = read_source(path)
        mutated, hits = apply_mutant(text, m["find"], m["replace"])
        if mutated is None:
            results.append({**m, "status": "invalid", "detail": f"'find' matched {hits} times (must be exactly 1)"})
            log(f"  {m['id']:<5} INVALID   ({hits} matches for 'find' in {m['file']})")
            continue
        try:
            try:
                path.write_bytes(mutated.encode(encoding))
            except UnicodeEncodeError:   # replacement has characters the file's encoding can't hold
                results.append({**m, "status": "invalid", "detail": f"'replace' can't be written as {encoding}"})
                log(f"  {m['id']:<5} INVALID   ('replace' can't be written as {encoding})")
                continue
            code, secs = run_tests(repo, test_cmd, timeout)
        finally:
            path.write_bytes(original)
        status = classify(code)
        results.append({**m, "status": status, "seconds": round(secs, 2)})
        log(f"  {m['id']:<5} {status.upper():<9} {m['file']}  ({m['antigen']})")
    return results


def summarize(repo_name, antigens, results, label=""):
    valid = [r for r in results if r["status"] != "invalid"]
    caught = sum(r["status"] in CAUGHT for r in valid)
    return {"repo": repo_name, "label": label, "antigens": antigens, "results": results,
            "killed": caught, "total": len(valid),
            "timeouts": sum(r["status"] == "timeout" for r in valid),
            "invalid": len(results) - len(valid),
            "immunity": round(caught / len(valid) * 100) if valid else 0}


# ── CLI ─────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mutants")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--test", default="npm test --silent")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("-o", "--out", default="results.json")
    ap.add_argument("--html")
    ap.add_argument("--compare", help="earlier results.json to show before/after")
    ap.add_argument("--label", default="", help="shown in the report title, e.g. 'held-out mutants'")
    ap.add_argument("--changed-since", metavar="REF", help="PR mode: only mutants in files changed since REF")
    ap.add_argument("--markdown", help="write a PR-comment style Markdown summary")
    ap.add_argument("--min-immunity", type=int, metavar="PCT",
                    help="CI gate: exit with code 2 if immunity is below PCT, or any mutant is invalid (stale)")
    args = ap.parse_args(argv)

    spec = json.loads(Path(args.mutants).read_text(encoding="utf-8"))
    repo = Path(args.repo)
    mutants = spec["mutants"]
    if args.changed_since:
        changed = changed_files(repo, args.changed_since)
        mutants = [m for m in mutants if m["file"] in changed]
        print(f"PR mode: {len(changed)} changed file(s) since {args.changed_since}, {len(mutants)} mutant(s) apply")

    baseline_or_exit(repo, args.test, args.timeout)

    results = run_mutants(mutants, repo, args.test, args.timeout)
    out = summarize(repo.resolve().name, spec["antigens"], results, args.label)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print_summary(out, args.out)

    if args.html:
        before = json.loads(Path(args.compare).read_text(encoding="utf-8")) if args.compare else None
        Path(args.html).write_text(render(out, before), encoding="utf-8")
        print(f"Wrote {args.html}")
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(out), encoding="utf-8")
        print(f"Wrote {args.markdown}")
    if args.min_immunity is not None:
        sys.exit(gate(out, args.min_immunity))


def baseline_or_exit(repo, test_cmd, timeout):
    code, _, output = run_tests(repo, test_cmd, timeout, with_output=True)
    if code != 0:
        hint = explain_failure(output)
        sys.exit("Baseline tests fail on the unmodified code, so results would be meaningless.\n"
                 f"Command: {test_cmd}\n--- last lines of output ---\n{output}\n"
                 + (f"---\n{hint}" if hint else ""))


def print_summary(out, path):
    if not out["results"]:
        print(f"\nNo stored mutants apply here, so there was nothing to re-inject.  -> {path}")
        return
    extra = "".join([f", {out['timeouts']} by timeout" if out["timeouts"] else "",
                     f"; {out['invalid']} invalid mutant(s) skipped" if out["invalid"] else ""])
    print(f"\nImmunity: {out['killed']}/{out['total']} ({out['immunity']}%){extra}  -> {path}")


def gate(out, min_immunity):
    """Return the CI exit code for a summarized run (0 pass, 2 fail) and print why."""
    if out["invalid"]:
        print(f"GATE FAILED: {out['invalid']} stale mutant(s): the code moved on; re-run the Bob hunt to refresh them.")
        return 2
    if out["total"] == 0:
        print("GATE PASSED: no known bug patterns apply to these files.")
        return 0
    if out["immunity"] < min_immunity:
        print(f"GATE FAILED: immunity {out['immunity']}% is below the required {min_immunity}%.")
        return 2
    print(f"GATE PASSED: immunity {out['immunity']}% >= {min_immunity}%.")
    return 0


# ── Markdown (PR comment) ───────────────────────────────────────────────────

def first_line(s):
    return (s.splitlines() or [""])[0]


def md(text, code=False):
    """Neutralise text from mutants/antigens before it goes into a PR comment: no fence or backtick
    breakouts, no raw HTML, no @mentions that would ping people."""
    text = redact_text(str(text)).replace("\r", " ").replace("\n", " ")
    if code:
        return text.replace("`", "'")
    text = text.replace("`", "'").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"@(?=[A-Za-z0-9])", "@​", text)


def fence(text):
    """Text for inside a ``` code block: keep the code exactly (including backticks), redact secrets,
    and break only a triple-backtick run, the one thing that could end the block early."""
    return redact_text(str(text)).replace("\r", " ").replace("\n", " ").replace("```", "``\u200b`")


def render_markdown(r, new_code=None):
    """PR comment. Two independent checks, reported separately so a green result is never implied
    for code that wasn't checked:
      1. stored mutants in changed files: would the tests catch those past bugs?
      2. new_code: lines this PR adds that match a known bug signature (None = not checked,
         because no knowledge base was available)."""
    antigens = {a["id"]: a for a in r["antigens"]}
    risky = [x for x in r["results"] if x["status"] == "survived"]
    problems = len(risky) + len(new_code or [])
    if problems:
        head = f"⚠️ {problems} past bug{'s' if problems > 1 else ''} could come back in this PR"
    elif not r["results"] and new_code is None:
        head = "ℹ️ Nothing in this PR could be checked"
    else:
        head = "✅ No known bugs found in this PR"
    lines = [f"### 💉 Bug Vaccine: {head}\n"]

    lines.append("**New code vs. company bug history**")
    if new_code is None:
        lines.append("Not checked: no knowledge base found. Add `.bugvaccine/company-knowledge.json` "
                     "(`bugvaccine.py learn`) so new code is compared with past bugs.\n")
    elif new_code:
        lines.append("Lines this PR adds match bugs the company has already fixed:\n")
        for f in new_code:
            a = f["antigen"]
            lines.append(f"- `{md(f['file'], code=True)}:{f['line']}` **{md(a.get('title', f['key']))}** "
                         f"({md(a.get('repo', ''))}): {md(f['explain'])}")
            if f.get("fix"):
                lines.append(f"  Suggested fix (the company's own past fix):\n  ```diff\n  - {fence(f['text'])}\n  + {fence(f['fix'])}\n  ```")
            else:
                lines.append(f"  ```\n  {fence(f['text'])}\n  ```")
                hint = a.get("signatures", {}).get("fix_hint")
                if hint:
                    lines.append(f"  How it was fixed before: {md(hint)}")
        if any(f.get("fix") for f in new_code):
            lines.append("\nApply every suggested fix, re-run the tests and re-check, in one step:\n"
                         "```\npython bugvaccine.py patch . --base <base-branch> --apply\n```")
        lines.append("")
    else:
        lines.append("No added line matches a known company bug.\n")

    lines.append("**Tests vs. past bugs in the changed files**")
    if not r["results"]:
        lines.append("No stored checks cover the files this PR changes.")
    elif risky:
        lines.append(f"{r['killed']}/{r['total']} caught. These past bugs could return and no test would notice:\n")
        for x in risky:
            a = antigens.get(x["antigen"], {})
            lines.append(f"- **{md(a.get('title', x['antigen']))}** in `{md(x['file'], code=True)}`: {md(x.get('why', ''))}")
            lines.append(f"  ```diff\n  - {fence(first_line(x['find']))}\n  + {fence(first_line(x['replace']))}\n  ```")
            if a.get("postmortem"):
                lines.append(f"  Past incident: `{md(a['postmortem'], code=True)}`")
        lines.append("\nSuggested: add a test that fails when the change above is applied.")
    else:
        lines.append(f"{r['killed']}/{r['total']} caught. Every stored check that applies is covered by a test.")
    return "\n".join(lines) + "\n"


# ── HTML report ─────────────────────────────────────────────────────────────

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--text:#16181d;--muted:#667085;--line:#e4e7ec;--good:#157347;--good-bg:#e3f4ea;
--bad:#b42318;--bad-bg:#fdecea;--ring:#e4e7ec;--del:#fdecea;--add:#e3f4ea}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111317;--card:#1a1d23;--text:#eceef2;
--muted:#98a2b3;--line:#2b2f37;--good:#5dd39e;--good-bg:#12301f;--bad:#ff8a7a;--bad-bg:#3a1714;--ring:#2b2f37;
--del:#3a1714;--add:#12301f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1000px;margin:0 auto;padding:32px 16px 64px}h1{margin:0;font-size:28px}.muted{color:var(--muted)}
.hero{display:flex;gap:24px;align-items:center;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin:20px 0}
.gauge{--p:0;width:130px;height:130px;border-radius:50%;display:grid;place-items:center;
background:conic-gradient(var(--good) calc(var(--p)*1%),var(--ring) 0)}
.gauge div{width:104px;height:104px;border-radius:50%;background:var(--card);display:grid;place-items:center;font-size:28px;font-weight:700}
.stat{font-size:14px}.stat b{font-size:22px;display:block}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:16px}
h2{margin:0 0 12px;font-size:18px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}
th{text-align:left;font-size:12px;color:var(--muted);font-weight:500;padding:8px;border-bottom:1px solid var(--line)}
td{padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}
.pill{font-size:12px;font-weight:700;padding:2px 10px;border-radius:99px;white-space:nowrap}
.killed,.timeout{background:var(--good-bg);color:var(--good)}.survived{background:var(--bad-bg);color:var(--bad)}.invalid{background:var(--line);color:var(--muted)}
code,pre{font-family:ui-monospace,Consolas,monospace;font-size:12.5px}.sub{color:var(--muted);font-size:13px}
pre.diff{margin:6px 0 0;padding:6px 8px;border-radius:6px;border:1px solid var(--line);white-space:pre-wrap;word-break:break-word}
pre.diff span{display:block}.d{background:var(--del)}.a{background:var(--add)}
details summary{cursor:pointer;color:var(--muted);font-size:12px;margin-top:4px}
.steps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.steps li{border:1px solid var(--line);border-radius:10px;padding:12px}.steps b{display:block}
.who{display:inline-block;margin:4px 0;font-size:11px;font-weight:700;padding:1px 8px;border-radius:99px;background:var(--line);color:var(--muted)}
.who.bob{background:#e8e3ff;color:#4b3bc7}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .who.bob{background:#2a2450;color:#b9adff}}
"""

PILL = {"killed": "🛡 caught", "timeout": "⏱ caught (timeout)", "survived": "⚠ slipped through", "invalid": "invalid"}
PIPELINE = [("Mine", "tool", "bug-fix commits + postmortems from history"),
            ("Extract antigens", "Bob", "the reusable pattern behind each bug"),
            ("Hunt", "Bob · parallel subagents", "every place each pattern could recur"),
            ("Re-infect", "tool", "inject each old bug, run tests, restore"),
            ("Antibodies", "Bob", "tests that guard each bug pattern"),
            ("Prove", "tool", "re-run, plus held-out mutants Bob never saw")]


def pill(status):
    return f'<span class="pill {status}">{PILL[status]}</span>'


def diff_block(find, replace):
    minus = "".join(f'<span class="d">- {html.escape(l)}</span>' for l in find.splitlines())
    plus = "".join(f'<span class="a">+ {html.escape(l)}</span>' for l in replace.splitlines())
    return f'<details><summary>show injected change</summary><pre class="diff">{minus}{plus}</pre></details>'


def render(r, before=None):
    antigens = {a["id"]: a for a in r["antigens"]}
    prev = {x["id"]: x["status"] for x in before["results"]} if before else {}
    before_head = "<th>Before</th>" if before else ""
    rows = []
    for x in r["results"]:
        a = antigens.get(x["antigen"], {})
        source = " · ".join(filter(None, [
            f'fix commit: “{html.escape(a["source_commit"])}”' if a.get("source_commit") else "",
            f'postmortem: <code>{html.escape(a["postmortem"])}</code>' if a.get("postmortem") else ""]))
        rows.append(
            "<tr>"
            + (f'<td>{pill(prev[x["id"]]) if x["id"] in prev else "—"}</td>' if before else "")
            + f'<td>{pill(x["status"])}</td>'
            f'<td>{html.escape(a.get("title", x["antigen"]))}<div class="sub">{html.escape(x.get("why", ""))}</div>'
            f'<div class="sub">{source}</div>{diff_block(x["find"], x["replace"])}</td>'
            f'<td><code>{html.escape(x["file"])}</code></td></tr>')
    steps = "".join(
        f'<li><b>{i}. {html.escape(n)}</b><span class="who{" bob" if "Bob" in who else ""}">{html.escape(who)}</span>'
        f'<div class="sub">{html.escape(d)}</div></li>'
        for i, (n, who, d) in enumerate(PIPELINE, 1))
    compare = ""
    if before:
        compare = (f'<div class="stat">Before vaccination<b>{before["killed"]}/{before["total"]} ({before["immunity"]}%)</b></div>'
                   f'<div class="stat">Change<b style="color:var(--good)">+{r["immunity"] - before["immunity"]} pts</b></div>')
    survivors = sum(x["status"] == "survived" for x in r["results"])
    title = "Bug Vaccine — immunity report" + (f" ({html.escape(r['label'])})" if r.get("label") else "")
    notes = []
    if r.get("timeouts"):
        notes.append(f'{r["timeouts"]} mutant(s) timed out and are counted as caught.')
    if r.get("invalid"):
        notes.append(f'{r["invalid"]} invalid mutant(s) skipped (their "find" text did not match exactly once).')
    note_html = f'<p class="sub">{" ".join(notes)}</p>' if notes else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bug Vaccine Report</title><style>{CSS}</style></head><body><main>
<h1><svg width="34" height="34" viewBox="0 0 64 64" aria-hidden="true" style="vertical-align:-6px;margin-right:6px"><path d="M32 3.5 55 11v19.5C55 45 45.5 55 32 60.5 18.5 55 9 45 9 30.5V11Z" fill="#2456A6"/><path d="M32 7.8 51.2 14v16.6c0 12.4-8 21-19.2 25.7C20.8 51.6 12.8 43 12.8 30.6V14Z" fill="#F4F8FF"/><g fill="#1D7A4E"><circle cx="22" cy="21.5" r="3.7"/><circle cx="32" cy="21.5" r="3.7"/><circle cx="42" cy="21.5" r="3.7"/><circle cx="22" cy="31.5" r="3.7"/><circle cx="42" cy="31.5" r="3.7"/><circle cx="22" cy="41.5" r="3.7"/><circle cx="32" cy="41.5" r="3.7"/><circle cx="42" cy="41.5" r="3.7"/></g><ellipse cx="32" cy="32.2" rx="3.3" ry="4.1" fill="#B42A1F"/></svg>{title}</h1>
<p class="muted">Every past bug in <code>{html.escape(r["repo"])}</code>'s history, re-injected into today's code. Would your tests catch it?</p>
<div class="hero"><div class="gauge" style="--p:{r["immunity"]}"><div>{r["immunity"]}%</div></div>
<div class="stat">Old bugs caught by tests<b>{r["killed"]}/{r["total"]}</b></div>
<div class="stat">Could come back unnoticed<b style="color:var(--bad)">{survivors}</b></div>{compare}</div>
{note_html}
<section><h2>Re-injected bugs</h2><div class="scroll"><table><thead><tr>{before_head}<th>{"After" if before else "Result"}</th><th>Historical bug / how it was re-injected</th><th>Where</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div></section>
<section><h2>How Bug Vaccine works</h2><ol class="steps">{steps}</ol></section>
</main></body></html>"""


if __name__ == "__main__":
    main()
