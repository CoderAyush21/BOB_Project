# Prompt 3 — Vaccinate (Bob, Agent mode)

> Screenshot the session summary → `screenshots/`.

---

1. Run the baseline:
   `python vaccine/run.py mutants.json --repo demo-repo -o results-before.json --html report-before.html`
2. For each **SURVIVED** mutant, write an **antibody** in `demo-repo/test/antibodies.test.js`. Name each test `antibody <antigen id>: <behaviour>`.

   **Antibodies must guard the bug PATTERN, not the single mutant.** A test that only catches the exact change in `mutants.json` is overfitted and will fail the held-out check in step 4. For each antigen:
   - test **every function** the pattern applies to, not just the one where the mutant was;
   - use **many inputs and boundaries**: all page sizes including the last partial page; missing, `null` and `undefined` nested objects; every cent value 0.01–0.99, alone and in pairs;
   - assert the *invariant* the original fix protects (e.g. "pages tile the list exactly," "money sums are exact to the cent").
3. Do NOT change anything in `demo-repo/src/`. The code is correct; the tests are what's missing.
4. Re-run:
   `python vaccine/run.py mutants.json --repo demo-repo -o results-after.json --compare results-before.json --html report.html`
5. Repeat step 2 for any survivors until immunity is 100%, or explain why a mutant can't be killed (for example, if it's equivalent to the original code).
6. Commit the antibody tests in `demo-repo` with a message listing which past bugs they protect against.
