# Phase 3: Re-infect and vaccinate (Agent mode)

**Before you start:** `git pull`. Replace `<MEMBER>` below with your first name. Then paste everything below the line into IBM Bob (Agent mode).
**Needs:** Phases 1–2 (`antigens.json`, `mutants.json`). **Unlocks:** Phase 4.

---

My name is **<MEMBER>**. You are running **Phase 3: Re-infect and vaccinate** of Bug Vaccine.

1. Read `bob-prompts/team/_shared-context.md` and follow its rules for this whole session. PHASE = 3, MEMBER = <MEMBER>.
2. Setup: `python tools/setup_phase.py 3`. If it fails, stop and tell me.
3. Baseline:
   `python vaccine/run.py bob-output/mutants.json --repo demo-repo -o bob-output/results-before.json --html bob-output/report-before.html`
   Any `INVALID` mutant has a wrong `find`: fix it in `bob-output/mutants.json`, note it in your log, and re-run.
4. 📸 `-Name p3-<MEMBER>-report-before -Html bob-output/report-before.html`
5. For each SURVIVED mutant, write antibodies in `demo-repo/test/antibodies.test.js` (Node's built-in `node:test` + `node:assert/strict`, like the existing tests). Name each one `antibody <antigen id>: <behaviour>`.
   **Guard the pattern, not the mutant.** A different teammate will later test your antibodies against new mutants you never see (Phase 4), so a test that only catches the exact change in `mutants.json` will fail there. For each antigen:
   - test **every function** the pattern applies to;
   - use **many inputs and boundaries**: all page sizes including partial last pages; missing/`null`/`undefined` nested objects; every cent value 0.01–0.99, alone and in pairs;
   - assert the **invariant** the original fix protects (e.g. "pages tile the list exactly," "money sums are exact to the cent").
   Do **not** change `demo-repo/src/`.
6. Re-run:
   `python vaccine/run.py bob-output/mutants.json --repo demo-repo -o bob-output/results-after.json --compare bob-output/results-before.json --html bob-output/report.html`
   Iterate until 100%, or explain in your log why a mutant can't be killed.
7. Copy the antibodies to the handoff folder: `Copy-Item demo-repo/test/antibodies.test.js bob-output/antibodies.test.js`
8. 📸 `-Name p3-<MEMBER>-report-after -Html bob-output/report.html`
9. Write your log (before → after immunity, number of antibody tests, iterations needed), commit, and finish as the shared rules describe.
