# Phase 1: Extract antigens (document understanding)

**Before you start:** `git pull`. Replace `<MEMBER>` below with your first name. Then paste everything below the line into IBM Bob (Agent mode).
**Needs:** nothing, since this is the first phase. **Unlocks:** Phases 2 and 5.

---

My name is **<MEMBER>**. You are running **Phase 1: Extract antigens** of Bug Vaccine.

1. Read `bob-prompts/team/_shared-context.md` and follow its rules for this whole session. PHASE = 1, MEMBER = <MEMBER>.
2. Setup: run `python -m unittest discover tests` (all must pass), then `python tools/setup_phase.py 1`. If either fails, stop and tell me.
3. Mine: `python vaccine/mine.py demo-repo -o bob-output/antigens-raw.md`.
4. Read `bob-output/antigens-raw.md` **and every incident document it lists** (e.g. `demo-repo/docs/postmortems/*.md`). This is the document-understanding step, so show your reasoning.
5. For each genuine bug fix, extract an **antigen**: the reusable pattern (not the specific line), its fix commit, its postmortem (if any), whether a regression test shipped with the fix, and any postmortem follow-up that the code shows was never done.
6. Write `bob-output/antigens.json`:
   `{"antigens": [{"id": "A<issue number>", "source_commit", "title", "pattern", "postmortem", "unfinished_followups": [...], "signatures": {...}}]}`
   **Teach the debugger.** Add a `signatures` block to each antigen, so later pull requests and the Debug lab can recognise this bug:
   `{"lang": "javascript", "code": [{"regex": "...", "explain": "..."}], "errors": ["..."], "fix_hint": "...", "example": {"before": "...", "after": "..."}, "antibody": "..."}`
   - `code` regexes describe the risky line; `errors` regexes describe the error message or bug report (from the fix commit, issue or postmortem).
   - Regexes must work in **both Python and JavaScript**: no `(?P<name>)`, no inline flags like `(?i)`, and no nested quantifiers such as `(a+)+`.
   - `code` regexes must **not** match today's fixed code. Check: `python bugvaccine.py learn --source invoice-kit=bob-output/antigens.json -o bob-output/knowledge.json`, then `python bugvaccine.py debug --kb bob-output/knowledge.json --scan demo-repo/src/*.js` must report no code matches.
7. 📸 `-Name p1-<MEMBER>-antigens` with `bob-output/antigens.json` open in the editor.
8. Write your log, commit, and finish as the shared rules describe.
