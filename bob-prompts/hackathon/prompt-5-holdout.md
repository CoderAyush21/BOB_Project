# Prompt 5: The blind check (fresh session)

**Before pasting: start a brand-new Bob chat/session.** This check only means something if you have never seen the mutants or the antibody tests. If someone else on the team can run it, even better.

---

You are running **Prompt 5 of 7** of the Bug Vaccine hackathon run. **Bob feature showcased: a fresh subagent for an independent, blind check.**

This measures whether the antibody tests from prompt 4 guard the bug **patterns**, or only memorised the specific mutants they were written against.

1. Read `bob-prompts/hackathon/_context.md` and follow it. N = 5. Do its "start of every prompt" step.
2. **Blindness rules:** do NOT open `bob-output/mutants.json`, `bob-output/antibodies.test.js`, `demo-repo/test/antibodies.test.js`, any `bob-output/results-*` or `report*` file, or earlier logs. You may read only `bob-output/antigens.json` and `demo-repo/src/`.
3. If `demo-repo/` is missing, rebuild it (`python demo/build_demo_repo.py`), then copy `bob-output/antibodies.test.js` to `demo-repo/test/` **without opening it**.
4. Design **2 new mutants per antigen**, each a *different* way to bring the same bug back than simply reverting the fix (for example an off-by-one at the start instead of the end, a guard removed while the default is kept, a rounding step dropped). If subagents are available, use a fresh one per antigen. Same format as usual; ids H1, H2, …; `find` must match exactly once.
5. Save them as `bob-output/mutants.holdout.json` (`{"antigens": [...], "mutants": [...]}`) and run:
   `python vaccine/run.py bob-output/mutants.holdout.json --repo demo-repo -o bob-output/results-holdout.json --label "held-out mutants" --html bob-output/report-holdout.html`
   Fix any `INVALID` mutant's `find` and re-run. **Never change the antibody tests.**
6. Report the held-out immunity **exactly as printed**, even if it's low: that's an honest finding. For each survivor, describe what kind of test would have caught it.
7. 📸 `-Name p5-report-holdout -Html bob-output/report-holdout.html`
8. Finish with the end-of-prompt steps in `_context.md` (commit "Bob prompt 5: blind held-out check, <score>%").
