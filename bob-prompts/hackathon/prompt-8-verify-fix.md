# Prompt 8: Verify the post-run fix and check the deliverables

**Run this in a new Bob session.** Any team member can run it; a teammate who hasn't used Bob on this project yet should, because the hackathon wants session screenshots from **every** team member. Before pasting, replace `<YOUR NAME>` and, if you have it, `<VIDEO LINK>`.

---

You are running **Prompt 8** of the Bug Vaccine hackathon run, for team member **<YOUR NAME>**. **Bob features showcased: code review of someone else's change, and independent verification in Agent mode.**

After the 7-prompt run, a bug was found and fixed **outside Bob** (with Claude): `bugvaccine.py patch --staged` also patched Bug Vaccine's own knowledge file when it was staged in the same commit. Your job is to check that fix independently, not to trust it.

1. Read `bob-prompts/hackathon/_context.md` and follow it. N = 8. Do its "start of every prompt" step.
2. **Review the change.** Find the commit with `git log --oneline -5 -- vaccine/patch.py`, then read it with `git show <commit> -- vaccine/patch.py tests/test_cure.py`. In your log, explain in plain words what was wrong, what changed, and whether the fix is complete. Look for any other way a non-code file could still get patched: explicit file arguments, `--base`, upper-case extensions, paths with `.bugvaccine` in the middle.
3. **Reproduce the original scenario** in a throwaway copy, so `demo-repo/` stays untouched:
   - `python demo/build_demo_repo.py $env:TEMP\bv-check`, then create `$env:TEMP\bv-check\.bugvaccine\` and copy `bob-output/knowledge.json` into it as `company-knowledge.json`.
   - `python bugvaccine.py guard install $env:TEMP\bv-check`
   - Write `export const firstPage = (xs, n) => xs.slice(0, 0 + n - 1);` to `$env:TEMP\bv-check\src\paging2.js`, then `git -C $env:TEMP\bv-check add -A`. This stages the knowledge file **and** the bug.
   - Record the knowledge file's hash (`Get-FileHash`).
   - `git -C $env:TEMP\bv-check commit -m "feat: paging helper"`. It must be **blocked**.
   - From inside that folder: `python <full path to bugvaccine.py> patch . --staged --apply --test "node --test"`. It must fix **only** `src/paging2.js`.
   - Check the knowledge file's hash is **unchanged**, then commit again. It must go through.
   - 📸 `-Name p8-fix-verified`, with the patch output visible.
   - Delete `$env:TEMP\bv-check`.
4. **Run the whole test suite:** `python -m unittest discover -s tests`. Copy the final `Ran N tests … OK` line into your log exactly.
5. **Video link:** if the link here is not `<VIDEO LINK>`, add `**▶ [Watch the demo video](<VIDEO LINK>)**` on its own line directly under the title in `README.md`, and use the same link in the "Demo video" row of the deliverables table in step 6. Otherwise skip this and write "video link: not provided yet" in your log.
6. **Deliverables check.** Add a section "## Submission checklist" at the end of `docs/challenge-alignment.md`, with a table of every lablab.ai deliverable and the file or link that meets it:
   - video demonstration;
   - written problem and solution statement;
   - written statement on how IBM Bob was used;
   - code repository including IBM Bob task session summary screenshots;
   - publicly accessible link to the repository;
   - each team member's screenshots of IBM Bob task session summaries;
   - no IBM Cloud credentials in the repo.

   Check each one yourself: open the file, or run `python tools/leak_scan.py` for the last one. Mark anything missing as ❌ with what's needed. Don't mark something ✅ that you didn't verify.
7. **Team table:** in `docs/how-bob-was-used.md`, under "Team members' Bob sessions", add a row for **<YOUR NAME>**: "Prompt 8: independent review and verification of the post-run `patch` fix, and final deliverables check". Use `bob_sessions/<YOUR NAME> - Prompt 8 summary.png` as the screenshot. Don't change the existing rows.
8. Write `bob-output/logs/prompt-8.md` (see `_context.md`), including the review from step 2 and every result from steps 3–4, copied from command output.
9. Finish with the end-of-prompt steps in `_context.md` (commit "Bob prompt 8: verify the patch fix and check the deliverables"). At the very end, tell me to save this session's summary as `bob_sessions/<YOUR NAME> - Prompt 8 summary.png` and push it:
   `git add bob_sessions; git commit -m "bob_sessions: <YOUR NAME> prompt 8 summary"; git push origin main`
