# Prompt 4: Re-infect and vaccinate (Agent mode)

---

You are running **Prompt 4 of 7** of the Bug Vaccine hackathon run. **Bob feature showcased: Agent mode (run, write, iterate).**

1. Read `bob-prompts/hackathon/_context.md` and follow it. N = 4. Do its "start of every prompt" step.
2. If `demo-repo/` is missing, rebuild it with `python demo/build_demo_repo.py`.
3. **Baseline:** `python vaccine/run.py bob-output/mutants.json --repo demo-repo -o bob-output/results-before.json --html bob-output/report-before.html`. An `INVALID` mutant has a wrong `find`: fix it in `bob-output/mutants.json`, note it in your log, and re-run.
4. 📸 `-Name p4-report-before -Html bob-output/report-before.html`
5. **Write antibodies** for every SURVIVED mutant in `demo-repo/test/antibodies.test.js` (`node:test` + `node:assert/strict`, like the existing tests), named `antibody <antigen id>: <behaviour>`.
   **Guard the pattern, not the mutant:** a later, blind check (prompt 5) uses mutants you will never see. For each antigen:
   - test **every function** the pattern applies to;
   - use **many inputs and boundaries**: all page sizes including partial last pages; missing, `null` and `undefined` nested objects; every cent value 0.01–0.99, alone and in pairs;
   - assert the **invariant** the original fix protects.
   Do **not** change `demo-repo/src/`.
6. **Re-run:** `python vaccine/run.py bob-output/mutants.json --repo demo-repo -o bob-output/results-after.json --compare bob-output/results-before.json --html bob-output/report.html`. Iterate until 100%, or explain in your log why a mutant can't be killed.
7. Commit the antibodies **inside** the patient too: `git -C demo-repo add -A; git -C demo-repo commit -m "test: antibodies for past bugs"`. Then copy them into the submission: `Copy-Item demo-repo/test/antibodies.test.js bob-output/antibodies.test.js`.
8. 📸 `-Name p4-report-after -Html bob-output/report.html`
9. Finish with the end-of-prompt steps in `_context.md` (commit "Bob prompt 4: re-infect and vaccinate, immunity <before>% to <after>%", using the real numbers).
