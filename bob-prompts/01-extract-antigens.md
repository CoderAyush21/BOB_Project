# Prompt 1 — Extract antigens from history and incident docs (Bob, Ask/Plan mode)

> Screenshot the session summary → `screenshots/`.

---

Run `python vaccine/mine.py demo-repo -o antigens-raw.md`. Then read:
1. `antigens-raw.md`: every bug-fix commit and its diff.
2. Every incident document in the repo, e.g. `demo-repo/docs/postmortems/*.md`. Postmortems often explain the *real* root cause and list follow-ups that were never done.

For each genuine bug, extract an **antigen**: the reusable *pattern* of the mistake, not the specific line.
- Good: "summing currency as floats instead of integer cents"
- Bad: "line 3 of money.js was wrong"

Link each antigen to its fix commit and, if one exists, its postmortem. Flag any postmortem follow-up (e.g. "add a regression test") that the code shows was never done.

Write `antigens.json`: `{"antigens": [{"id", "source_commit", "title", "pattern", "postmortem", "unfinished_followups"}]}`.
Use ids like `A<issue number>`.

Then: **Teach the debugger.** Add a `signatures` block to each antigen, so later pull requests and the Debug lab can recognise this bug:
   `{"lang": "javascript", "code": [{"regex": "...", "explain": "..."}], "errors": ["..."], "fix_hint": "...", "example": {"before": "...", "after": "..."}, "antibody": "..."}`
   - `code` regexes describe the risky line; `errors` regexes describe the error message or bug report (from the fix commit, issue or postmortem).
   - Regexes must work in **both Python and JavaScript**: no `(?P<name>)`, no inline flags like `(?i)`, and no nested quantifiers such as `(a+)+`.
   - `code` regexes must **not** match today's fixed code. Check: `python bugvaccine.py learn --source invoice-kit=antigens.json -o knowledge.json`, then `python bugvaccine.py debug --kb knowledge.json --scan demo-repo/src/*.js` must report no code matches.
