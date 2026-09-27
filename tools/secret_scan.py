"""Block pushes that would leak credentials (the hackathon suspends IBM Cloud accounts whose keys
are found in a repo).

    python tools/secret_scan.py            # scan what's staged for commit (git diff --cached)
    python tools/secret_scan.py --all      # scan every tracked file (use before the first push)

Exit code 1 if anything looks like a credential. Uses the same rules as vaccine/redact.py.
Test files are allowed to contain obviously fake *assignments* (e.g. password: hunter2hunter2),
but real token formats (AWS, GitHub, Slack, JWT, private keys, URL credentials) are flagged everywhere.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vaccine"))

import redact  # noqa: E402

STRONG = {"private-key", "aws-access-key", "github-token", "slack-token", "jwt", "url-credentials"}
FAKE_OK = re.compile(r"^(tests|examples|docs)/|^\.env\.example$")
IBM_KEY = re.compile(r"\b(?:ibm[_-]?cloud[_-]?)?api[_-]?key\b[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_-]{40,48})", re.I)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout


def added_lines_staged():
    out, path = [], None
    for line in git("diff", "--cached", "-U0", "--no-color").splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and path:
            out.append((path, line[1:]))
    return out


def all_tracked_lines():
    out = []
    for path in git("ls-files").splitlines():
        p = ROOT / path
        if p.suffix.lower() in {".png", ".jpg", ".gif", ".ico", ".pdf"} or not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            out.append((path, line))
    return out


def scan(lines):
    hits = []
    for path, line in lines:
        for name, rx, _how in redact._COMPILED:
            if name not in STRONG and FAKE_OK.match(path):
                continue
            if rx.search(line):
                hits.append((path, name, line.strip()[:80]))
        if IBM_KEY.search(line) and not FAKE_OK.match(path):
            hits.append((path, "ibm-cloud-api-key", line.strip()[:80]))
    return hits


def main():
    lines = all_tracked_lines() if "--all" in sys.argv else added_lines_staged()
    hits = scan(lines)
    if not hits:
        print(f"secret scan: clean ({len(lines)} lines checked)")
        return
    print("secret scan: POSSIBLE CREDENTIALS FOUND. Do not push until these are removed and rotated:")
    for path, name, _text in hits:
        print(f"  {path}: {name}")   # never print the value itself
    sys.exit(1)


if __name__ == "__main__":
    main()
