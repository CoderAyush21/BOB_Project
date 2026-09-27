# Prompt 2: Learn from history (document understanding)

---

You are running **Prompt 2 of 7** of the Bug Vaccine hackathon run. **Bob feature showcased: document understanding.**

1. Read `bob-prompts/hackathon/_context.md` and follow it. N = 2. Do its "start of every prompt" step.
2. Build the patient: `python demo/build_demo_repo.py`, then `git -C demo-repo log --oneline`.
3. Mine the history: `python vaccine/mine.py demo-repo -o bob-output/antigens-raw.md`.
4. **Read** `bob-output/antigens-raw.md` **and every incident document it lists** (`demo-repo/docs/postmortems/*.md`). Show your reasoning: which commits are genuine bug fixes, which fixes shipped without a regression test, and which postmortem follow-ups the code shows were never done.
5. For each genuine bug, write an **antigen** into `bob-output/antigens.json`:
   `{"antigens": [{"id": "A<issue number>", "source_commit", "title", "pattern", "postmortem", "unfinished_followups": [...], "signatures": {...}}]}`
   - `pattern` is the reusable mistake, not the line ("summing currency as floats", not "line 3 of money.js").
   - `signatures`: `{"lang": "javascript", "code": [{"regex", "explain"}], "errors": [regex, ...], "fix_hint", "example": {"before", "after"}, "antibody", "patches": [{"regex", "replace", "explain"}]}`
   - `code` regexes describe the risky line; `errors` describe the error message or bug report; `patches` is a **fix recipe** that turns the buggy line into the fixed one, taken from the original fix commit (`$1`..`$9` for groups).
   - Every regex must work in **both Python and JavaScript**: no `(?P<name>)`, no inline flags like `(?i)`, no nested quantifiers like `(a+)+`.
6. **Prove the signatures are right:**
   - `python bugvaccine.py learn --source invoice-kit=bob-output/antigens.json -o bob-output/knowledge.json` (it rejects unsafe regexes).
   - `python bugvaccine.py debug --kb bob-output/knowledge.json --scan "demo-repo/src/*.js"` must report **no code matches** on today's fixed code. If it does, fix the regex and repeat.
   - Check each fix recipe restores the historical fix: write every antigen's `example.before` line into `demo-repo/src/_check.js` (one per line), run `python bugvaccine.py patch demo-repo src/_check.js --kb bob-output/knowledge.json` (a dry run), and confirm each proposed `+` line makes **the same fix** as that antigen's `example.after`. It may be more minimal (for example adding `?.` without a default value); say so in your log. If a line is reported as *needs a human or Bob*, the recipe doesn't cover that form: improve the recipe, or record that this form needs a human. Then delete `demo-repo/src/_check.js`.
7. 📸 `-Name p2-antigens` with `bob-output/antigens.json` open in the editor.
8. Finish with the end-of-prompt steps in `_context.md` (commit "Bob prompt 2: antigens, signatures and fix recipes from history").
