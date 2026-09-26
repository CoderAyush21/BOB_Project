"""Mine a repo's git history for bug-fix commits and incident docs.

Usage:  python vaccine/mine.py demo-repo -o antigens-raw.md

Output is a Markdown dossier Bob reads to extract "antigens": the reusable
bug pattern behind each fix. Detection is deliberately broad (it errs toward
including a commit); Bob decides which ones are real bug fixes.

A commit counts as a candidate fix when its full message (subject + body):
  - uses a fix word:            fix/fixes/fixed, bug, bugfix, hotfix, regression,
                                crash, patch, incident, postmortem, revert
  - or closes an issue:         resolves #12, closes #12, fixes #12
  - or uses a conventional tag: fix: / fix(scope):
"""
import argparse
import re
import subprocess
from pathlib import Path

from redact import redact, redact_text

FIX_WORDS = re.compile(
    r"\b(fix(e[sd])?|bug(fix)?|hotfix|regression|crash(es|ed)?|patch(es|ed)?|incident|post-?mortem|revert(s|ed)?)\b"
    r"|\b(resolve[sd]?|close[sd]?)\s+#\d+"
    r"|^fix(\([^)]*\))?!?:",
    re.I | re.M,
)
TEST_PATH = re.compile(r"(^|/)(test|tests|__tests__|spec)/|\.test\.|_test\.|\.spec\.|(^|/)test_")
INCIDENT_DOC = re.compile(r"(post-?mortem|incident|rca)", re.I)
SEP, END = "\x1f", "\x1e"


def is_fix(message):
    return bool(FIX_WORDS.search(message))


def touches_tests(files):
    return any(TEST_PATH.search(f) for f in files)


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def fix_commits(repo):
    log = git(repo, "log", "--reverse", f"--format=%H{SEP}%ad{SEP}%s{SEP}%b{END}", "--date=short")
    for record in filter(str.strip, log.split(END)):
        sha, date, subject, body = record.strip("\n").split(SEP)
        if is_fix(f"{subject}\n{body}"):
            yield sha, date, subject, body.strip()


def incident_docs(repo):
    files = git(repo, "ls-files").splitlines()
    return [f for f in files if f.lower().endswith((".md", ".txt", ".rst")) and INCIDENT_DOC.search(f)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("-o", "--out", default="antigens-raw.md")
    ap.add_argument("--max", type=int, default=50, help="max fix commits to include (most recent)")
    args = ap.parse_args(argv)

    fixes = list(fix_commits(args.repo))[-args.max:]
    docs = incident_docs(args.repo)

    parts = [f"# Bug-fix dossier for `{Path(args.repo).name}`\n",
             f"{len(fixes)} candidate fix commits, {len(docs)} incident document(s).\n"]
    redacted = 0
    if docs:
        parts.append("## Incident documents (read these too)\n" + "\n".join(f"- `{d}`" for d in docs) + "\n")
    for sha, date, subject, body in fixes:
        files = git(args.repo, "show", "--name-only", "--format=", sha).split()
        diff, found = redact(git(args.repo, "show", "--format=", "--unified=3", sha))
        body = redact_text(body)
        redacted += sum(found.values())
        parts.append(
            f"\n## {subject}\n- commit: `{sha[:10]}` · {date}\n- files: {', '.join(f'`{f}`' for f in files)}\n"
            f"- regression test added in same commit: **{'yes' if touches_tests(files) else 'NO'}**\n"
            + (f"- message body: {body}\n" if body else "")
            + f"\n```diff\n{diff.strip()}\n```\n"
        )
    Path(args.out).write_text("\n".join(parts), encoding="utf-8")
    note = f"; redacted {redacted} secret(s) found in history - rotate them if they were ever real" if redacted else ""
    print(f"Wrote {args.out} ({len(fixes)} fix commits, {len(docs)} incident docs{note})")


if __name__ == "__main__":
    main()
