# Phase 6: Write-up and verification

**Before you start:** `git pull`. Replace `<MEMBER>` below with your first name. Then paste everything below the line into IBM Bob (Agent mode).
**Needs:** Phases 1–5 all pushed. Best run by the team lead or whoever is submitting.

---

My name is **<MEMBER>**. You are running **Phase 6: Write-up and verification** of Bug Vaccine.

1. Read `bob-prompts/team/_shared-context.md` and follow its rules for this whole session. PHASE = 6, MEMBER = <MEMBER>.
2. Setup: `python tools/setup_phase.py 6`. If anything is missing, stop and tell me which phase hasn't been pushed.
3. **Re-verify every number yourself.** Don't trust the logs; re-run the measurements:
   ```
   python tools/setup_phase.py 3
   python vaccine/run.py bob-output/mutants.json --repo demo-repo -o verify-before.json
   python tools/setup_phase.py 4
   python vaccine/run.py bob-output/mutants.json --repo demo-repo -o verify-after.json
   python vaccine/run.py bob-output/mutants.holdout.json --repo demo-repo -o verify-holdout.json
   ```
   Compare with `bob-output/results-before.json`, `results-after.json` and `results-holdout.json`. Report any mismatch; don't hide it. Delete the `verify-*.json` files afterwards.
4. Read every file in `bob-output/logs/`. Fill in every `TODO` in `docs/how-bob-was-used.md`: which member ran which phase, the Bob features each one **actually** used, real numbers only, and the screenshot file names in `screenshots/auto/` and `screenshots/manual/`. Keep the transparency note that the initial scripts were drafted with another AI assistant (Claude); state which parts Bob produced (everything in `bob-output/`).
5. You may now open `examples/` **for the first time**. Compare `bob-output/mutants.json` with `examples/mutants.example.json`, and `bob-output/mutants.holdout.json` with `examples/mutants.holdout.json`. List the sites the team's Bob found that the reference missed, and the other way round. Add this to `docs/how-bob-was-used.md` under "What Bob found that we didn't expect."
6. If the measured results differ from `docs/problem-and-solution.md` or `README.md`, update those numbers. **Show me the diff and wait for my OK before saving.** Keep the prototype caveat only if it still applies.
7. Check which `screenshots/manual/phase-N-*-summary.png` files exist. List any phase whose summary screenshot is missing and who ran it (from the logs).
8. Security check: search the whole project for `apikey|api_key|password|secret|token|ibm_cloud` (case-insensitive), excluding `bob-prompts/`, `tools/` and `docs/`. Report file:line for anything suspicious; never print the values.
9. 📸 `-Name p6-<MEMBER>-final -Html bob-output/report.html`
10. Final report: a results table (known immunity before → after, held-out immunity, PR findings, antibody test count, `src/` untouched?), Bob features used by phase and member, missing screenshots, and anything that went wrong.
11. Write your log, commit, and finish as the shared rules describe. Then tell me: "Remaining: record the video (`docs/demo-video-script.md`), check the repo uses the IBM hackathon template, make it public, and submit."
