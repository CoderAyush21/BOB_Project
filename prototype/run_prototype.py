"""Bug Vaccine prototype: runs the whole workflow end to end with one command.

    python prototype/run_prototype.py            (pauses between steps)
    python prototype/run_prototype.py --no-pause

Steps marked [TOOL] are this repo's deterministic scripts.
Steps marked [BOB] are the AI steps. In this prototype they are filled by
pre-written stand-in outputs (prototype/bob-standin/, examples/) so you can
see the full flow before running it in IBM Bob. In the hackathon run, Bob
produces those files live from bob-prompts/.
"""
import json
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "prototype-output"
REPO = OUT / "demo-repo"
PY = sys.executable
BAR = "─" * 72
STEPS = 9
# Call the test runner directly: `npm test` adds ~1.5 s of npm start-up to every one of ~25 runs.
TEST = "node --test"


def step(n, who, title):
    tag = "[BOB] " if who == "bob" else "[TOOL]"
    print(f"\n{BAR}\n STEP {n}/{STEPS}  {tag}  {title}\n{BAR}")


def sh(*args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, check=True)


def git(*args):
    subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True)


def pause(msg):
    if "--no-pause" not in sys.argv:
        input(f"\n  ↳ {msg}  [Enter to continue] ")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def vaccine(mutants, out, *extra):
    sh(PY, "vaccine/run.py", str(mutants), "--repo", str(REPO), "--test", TEST, "-o", str(OUT / out), *extra)
    return load(OUT / out)


def main():
    # flush our prints before each child script writes, so steps appear in order
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
    t0 = time.time()
    if OUT.exists():
        try:
            with warnings.catch_warnings():  # git objects are read-only on Windows
                warnings.simplefilter("ignore", DeprecationWarning)
                shutil.rmtree(OUT, onerror=lambda f, p, _: (Path(p).chmod(0o666), f(p)))
        except PermissionError as e:
            sys.exit(f"Can't clear the previous demo output ({e.filename}).\n"
                     "Something is using it: a terminal whose current folder is inside prototype-output,\n"
                     "or an editor with a file open there. Close it or cd elsewhere, then run the demo again.")
    OUT.mkdir()

    step(1, "tool", "Mine the git history for bug fixes and incident docs")
    sh(PY, "demo/build_demo_repo.py", str(REPO))
    sh(PY, "vaccine/mine.py", str(REPO), "-o", str(OUT / "antigens-raw.md"))
    for line in (OUT / "antigens-raw.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## ") and not line.startswith("## Incident"):
            print(f"   • {line[3:]}")
        elif "regression test added" in line:
            print(f"       {line.strip('- ').replace('**', '')}")
        elif line.startswith("- `") and "postmortem" in line:
            print(f"   • incident doc: {line[2:].strip('`')}")
    pause("Bob now reads these diffs and the postmortem, and names the pattern behind each bug.")

    spec = load(ROOT / "examples/mutants.example.json")
    step(2, "bob", "Extract antigens (document understanding: diffs + postmortem)")
    for a in spec["antigens"]:
        print(f"   {a['id']}: {a['pattern']}")
        for f in a.get("unfinished_followups", []):
            print(f"        ⚠ postmortem follow-up never done: {f}")
    pause("Bob launches one subagent per antigen, in parallel, to hunt today's code.")

    step(3, "bob", "Hunt re-infection sites (1 subagent per antigen, in parallel)")
    for m in spec["mutants"]:
        print(f"   {m['id']} [{m['antigen']}] {m['file']:<18} {m['why']}")
    (OUT / "mutants.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    pause("Now inject each old bug, one at a time, and see whether the tests notice.")

    step(4, "tool", "Re-infect: inject each historical bug and run the tests")
    before = vaccine(OUT / "mutants.json", "results-before.json", "--html", str(OUT / "report-before.html"))
    pause("Bob writes antibody tests that guard each bug PATTERN, not just the one mutant.")

    step(5, "bob", "Write pattern-level antibody tests")
    shutil.copy(ROOT / "prototype/bob-standin/antibodies.test.js", REPO / "test/antibodies.test.js")
    for line in (REPO / "test/antibodies.test.js").read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("test(") and "antibody" in line:
            print("   + " + line.split("'")[1])
    git("add", "-A")
    git("commit", "-q", "-m", "test: antibodies for past bugs #41 #57 #63")
    print("   (committed to demo-repo; src/ untouched, only tests added)")
    pause("Re-run the vaccine on the known mutants.")

    step(6, "tool", "Prove it: re-run the known mutants and compare")
    after = vaccine(OUT / "mutants.json", "results-after.json",
                    "--compare", str(OUT / "results-before.json"), "--html", str(OUT / "report.html"))
    pause("But the antibodies were written while looking at those mutants. Are they overfitted?")

    step(7, "bob", "Held-out check: new mutants the antibody writer never saw")
    print("   A separate Bob subagent re-injects the same patterns in NEW ways.\n")
    holdout = vaccine(ROOT / "examples/mutants.holdout.json", "results-holdout.json",
                      "--label", "held-out mutants", "--html", str(OUT / "report-holdout.html"))
    pause("Finally: use it where it matters most, on a pull request.")

    step(8, "tool", "PR mode: PR #88 adds refunds.js and loyalty.js; does it bring old bugs back?")
    git("checkout", "-q", "-b", "feature/refunds")
    for rel in ("src/refunds.js", "test/refunds.test.js"):
        shutil.copy(ROOT / "examples/pr-refunds" / rel, REPO / rel)
    shutil.copy(ROOT / "examples/debug-samples/new-feature.js", REPO / "src/loyalty.js")  # repeats 3 known bugs
    git("add", "-A")
    git("commit", "-q", "-m", "feat: refunds and loyalty statements (#88)")
    # Company knowledge (also used by the Debug lab): this demo repo plus the real tomli case study
    subprocess.run([PY, "bugvaccine.py", "learn", "--source", f"invoice-kit={OUT / 'mutants.json'}",
                    "--source", f"tomli={ROOT / 'case-studies/tomli/mutants.json'}",
                    "-o", str(OUT / "knowledge.json")], cwd=ROOT, check=True, capture_output=True)
    # The real `pr` command, exactly as a company runs it: stored mutants + new code vs. company history
    subprocess.run([PY, "bugvaccine.py", "init", str(REPO), "--name", "invoice-kit", "--test", TEST,
                    "--force"], cwd=ROOT, check=True, capture_output=True)
    shutil.copy(ROOT / "examples/mutants.pr.json", REPO / ".bugvaccine/mutants.json")
    subprocess.run([PY, "bugvaccine.py", "pr", str(REPO), "--base", "main", "--kb", str(OUT / "knowledge.json"),
                    "-o", "results-pr.json"], cwd=ROOT, check=True)
    shutil.copy(REPO / ".bugvaccine/results-pr.json", OUT / "results-pr.json")
    shutil.copy(REPO / ".bugvaccine/pr-comment.md", OUT / "pr-comment.md")
    pr = load(OUT / "results-pr.json")
    print("\n   ┌─ PR comment Bug Vaccine would post ─────────────────────────────")
    for line in (OUT / "pr-comment.md").read_text(encoding="utf-8").splitlines():
        print(f"   │ {line}")
    print("   └─────────────────────────────────────────────────────────────────")
    pause("Bug Vaccine found them. Now cure them, and stop them coming back.")

    step(9, "tool", "Cure & prevent: apply the company's own past fixes, then guard every future commit")
    kb_path = str(OUT / "knowledge.json")
    cure = {}
    print("   Cure: patch the PR with the fixes the team already wrote (tests must still pass)\n")
    sh(PY, "bugvaccine.py", "patch", str(REPO), "--base", "main", "--kb", kb_path, "--apply", "--test", TEST,
       "--report", str(OUT / "patch-report.json"))
    cure["patch"] = load(OUT / "patch-report.json")
    git("commit", "-q", "-am", "fix: apply the company's known fixes for #41 #57 #63")
    subprocess.run([PY, "bugvaccine.py", "pr", str(REPO), "--base", "main", "--kb", kb_path,
                    "-o", "results-pr-after.json"], cwd=ROOT, check=True, capture_output=True)
    after_pr = load(REPO / ".bugvaccine/results-pr-after.json")
    cure["pr_after"] = {"new_code": len(after_pr.get("new_code") or []),
                        "untested": after_pr["total"] - after_pr["killed"], "total": after_pr["total"]}
    print(f"\n   Re-check PR #88: {cure['pr_after']['new_code']} added lines repeat known bugs now "
          f"(was {len(pr.get('new_code') or [])}).")

    print("\n   Prevent: install the pre-commit guard, then try to commit a new copy of bug #41")
    # where a company keeps its knowledge base: committed at .bugvaccine/company-knowledge.json
    shutil.copy(OUT / "knowledge.json", REPO / ".bugvaccine/company-knowledge.json")
    subprocess.run([PY, "bugvaccine.py", "guard", "install", str(REPO)], cwd=ROOT, check=True, capture_output=True)
    bad = "export const firstPage = (xs, n) => xs.slice(0, 0 + n - 1);\n"
    (REPO / "src/paging2.js").write_text(bad, encoding="utf-8")
    git("add", "-A")
    attempt = subprocess.run(["git", "commit", "-m", "feat: paging helper"], cwd=REPO, capture_output=True,
                             text=True, encoding="utf-8", errors="replace")
    blocked = attempt.returncode != 0
    cure["guard"] = {"blocked": blocked, "file": "src/paging2.js", "line": bad.strip(),
                     "output": (attempt.stdout + attempt.stderr).strip()[-1500:]}
    print(f"   {'BLOCKED' if blocked else 'NOT BLOCKED (unexpected)'}: git commit exited {attempt.returncode}")
    for line in cure["guard"]["output"].splitlines()[:6]:
        print(f"     {line}")
    git("reset", "-q", "HEAD", "src/paging2.js")
    (REPO / "src/paging2.js").unlink()
    subprocess.run([PY, "bugvaccine.py", "guard", "uninstall", str(REPO)], cwd=ROOT, capture_output=True)

    rules = subprocess.run([PY, "bugvaccine.py", "rules", "--kb", kb_path, "-o", str(OUT / "bug-vaccine.semgrep.yml")],
                           cwd=ROOT, check=True, capture_output=True, text=True).stdout
    cure["rules"] = {"count": int(rules.split()[1]), "file": "bug-vaccine.semgrep.yml"}
    print(f"\n   Prevent everywhere: exported {cure['rules']['count']} Semgrep rules for IDEs and CI "
          f"(prototype-output/bug-vaccine.semgrep.yml)")
    (OUT / "cure.json").write_text(json.dumps(cure, indent=2), encoding="utf-8")
    # history, RAG and the dashboard describe the project's main line, not this PR branch
    git("checkout", "-q", "main")

    # RAG index: the demo repo's fix commits and postmortem, plus both projects' learned bug patterns
    sh(PY, "bugvaccine.py", "index", str(REPO), "--source", f"invoice-kit={OUT / 'mutants.json'}",
       "--source", f"tomli={ROOT / 'case-studies/tomli/mutants.json'}", "-o", str(OUT / "rag-index.json"))
    sh(PY, "vaccine/dashboard.py", "--repo", str(REPO), "--knowledge", str(OUT / "knowledge.json"),
       "--rag", str(OUT / "rag-index.json"),
       "--before", str(OUT / "results-before.json"), "--after", str(OUT / "results-after.json"),
       "--holdout", str(OUT / "results-holdout.json"), "--pr", str(OUT / "results-pr.json"),
       "--antibodies", str(REPO / "test/antibodies.test.js"), "--title", "Bug Vaccine: invoice-kit",
       "--project", f"invoice-kit={OUT / 'results-before.json'},{OUT / 'results-after.json'}",
       "--project", f"tomli={ROOT / 'case-studies/tomli/results-before.json'}",
       "--diff-sample", str(ROOT / "examples/debug-samples/pr-88.diff"),
       "--cure", str(OUT / "cure.json"),
       "--web-fonts",   # demo data only, so loading IBM Plex from Google Fonts is fine here
       "-o", str(OUT / "dashboard.html"))

    print(f"\n{BAR}\n RESULTS")
    print(f"   Known mutants     immunity {before['immunity']}% → {after['immunity']}%"
          f"   ({after['killed'] - before['killed']} past bugs can no longer return unnoticed)")
    print(f"   Held-out mutants  immunity {holdout['immunity']}%   (new variants the antibodies were not written against)")
    new = len(pr.get("new_code") or [])
    print(f"   PR #88            {new} added line(s) repeat known company bugs; "
          f"{pr['total'] - pr['killed']} of {pr['total']} past bugs in changed files have no test")
    fixed = sum(len(f["changes"]) for f in cure["patch"]["files"])
    print(f"   Cure              {fixed} repeated bugs patched with the company's own fixes; tests "
          f"{cure['patch']['tests']}; re-scan {'clean' if cure['patch']['verified'] else 'NOT clean'}")
    print(f"   Prevent           guard {'blocked' if cure['guard']['blocked'] else 'did NOT block'} a new copy of bug #41; "
          f"{cure['rules']['count']} Semgrep rules exported")
    print(f"   Tool time {time.time() - t0:.0f}s (excludes Bob's steps)")
    print(f"\n   Open the interactive dashboard:  start prototype-output/dashboard.html")
    print(BAR)
    if "--open" in sys.argv:
        import webbrowser
        webbrowser.open((OUT / "dashboard.html").as_uri())


if __name__ == "__main__":
    main()
