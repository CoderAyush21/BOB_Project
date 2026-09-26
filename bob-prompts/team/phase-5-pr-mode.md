# Phase 5: PR mode (code review workflow)

**Before you start:** `git pull`. Replace `<MEMBER>` below with your first name. Then paste everything below the line into IBM Bob (Agent mode).
**Needs:** only Phase 1 (`antigens.json`), so **this can run in parallel with Phases 2–4.** **Unlocks:** Phase 6.

---

My name is **<MEMBER>**. You are running **Phase 5: PR mode** of Bug Vaccine.

This phase shows Bug Vaccine in the **code review** workflow: when a pull request adds new code, check whether it repeats a bug the repo has already shipped, and post a PR comment.

1. Read `bob-prompts/team/_shared-context.md` and follow its rules for this whole session. PHASE = 5, MEMBER = <MEMBER>.
2. Setup: `python tools/setup_phase.py 5`. If it fails, stop and tell me.
3. Simulate a PR: `git -C demo-repo checkout -b feature/refunds`. Copy **only** these files from `examples/`: `examples/pr-refunds/src/refunds.js` → `demo-repo/src/refunds.js`, `examples/pr-refunds/test/refunds.test.js` → `demo-repo/test/refunds.test.js`, and `examples/debug-samples/new-feature.js` → `demo-repo/src/loyalty.js`. Commit as `feat: refunds and loyalty statements (#88)`.
4. Build the company knowledge base from Phase 1: `python bugvaccine.py learn --source invoice-kit=bob-output/antigens.json -o bob-output/knowledge.json`.
5. List the changed files (`git -C demo-repo diff --name-only main...HEAD`). Launch **one subagent per antigen, in parallel**, checking **only those files** for places its pattern could recur, and merge their mutants into `bob-output/mutants.pr.json` (`{"antigens": [...], "mutants": [...]}`, ids P1, P2, …).
6. Set the repo up for PR mode: `python bugvaccine.py init demo-repo --name invoice-kit --test "npm test --silent" --force`, then copy `bob-output/mutants.pr.json` to `demo-repo/.bugvaccine/mutants.json`.
7. Run PR mode exactly as CI would: `python bugvaccine.py pr demo-repo --base main --kb bob-output/knowledge.json -o results-pr.json`. It runs **two checks** and reports them separately in one comment:
   - **new code vs. company bug history** (should flag `loyalty.js`, which repeats known bugs),
   - **tests vs. past bugs** in the changed files (should flag the untested `refunds.js`).
   Copy `demo-repo/.bugvaccine/pr-comment.md` and `demo-repo/.bugvaccine/results-pr.json` to `bob-output/`, and show the comment.
8. 📸 `-Name p5-<MEMBER>-pr-comment` with `bob-output/pr-comment.md` open.
9. Switch back: `git -C demo-repo checkout main`.
10. Write your log (which past bugs the PR repeats, and how the comment would help a reviewer), commit, and finish as the shared rules describe.
