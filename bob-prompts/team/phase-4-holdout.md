# Phase 4: Held-out check (the blind test)

**Before you start:** `git pull`. Replace `<MEMBER>` below with your first name. Then paste everything below the line into IBM Bob (Agent mode).
**Needs:** Phases 1 and 3 (`antigens.json`, `antibodies.test.js`). **Unlocks:** Phase 6.
**Best run by someone who did NOT run Phase 2 or 3,** in a brand-new Bob session. That's what makes this test blind.

---

My name is **<MEMBER>**. You are running **Phase 4: Held-out check** of Bug Vaccine.

This phase measures whether the antibody tests written in Phase 3 guard the bug **patterns**, or only memorised the specific mutants they were written against. You must stay **blind** to those mutants and tests.

1. Read `bob-prompts/team/_shared-context.md` and follow its rules for this whole session. PHASE = 4, MEMBER = <MEMBER>.
2. Setup: `python tools/setup_phase.py 4`. It rebuilds `demo-repo/` and re-applies Phase 3's antibody tests. If it fails, stop and tell me.
3. **Blindness rules:** do NOT open `bob-output/mutants.json`, `bob-output/antibodies.test.js`, `demo-repo/test/antibodies.test.js`, any `bob-output/results-*` or `report*` file, or other members' logs. You may read only `bob-output/antigens.json` and `demo-repo/src/`.
4. Design **2 new mutants per antigen**, each a *different* way to re-introduce that same bug pattern than simply reverting the fix. For example: an off-by-one at the start instead of the end, a null guard removed while the default is kept, a rounding step dropped. Use the usual format; `find` must match exactly once; ids H1, H2, … If subagents are available, use a fresh one per antigen.
5. Save as `bob-output/mutants.holdout.json` (`{"antigens": [...], "mutants": [...]}`).
6. Run:
   `python vaccine/run.py bob-output/mutants.holdout.json --repo demo-repo -o bob-output/results-holdout.json --label "held-out mutants" --html bob-output/report-holdout.html`
   Fix any `INVALID` mutant's `find` text and re-run. **Never change the antibody tests.**
7. 📸 `-Name p4-<MEMBER>-report-holdout -Html bob-output/report-holdout.html`
8. Report the held-out immunity **exactly as printed**, even if it's low. A low score is a real, honest finding. For each survivor, describe what kind of test would have caught it.
9. Write your log, commit, and finish as the shared rules describe.
