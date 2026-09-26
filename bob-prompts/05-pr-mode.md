# Prompt 5 — PR mode (Bob, Agent mode + parallel subagents)

> Screenshot the session summary → `screenshots/`.

---

1. Simulate a PR: `git -C demo-repo checkout -b feature/refunds`. Copy **only** these files from `examples/`: `examples/pr-refunds/src/refunds.js` → `demo-repo/src/refunds.js`, `examples/pr-refunds/test/refunds.test.js` → `demo-repo/test/refunds.test.js`, and `examples/debug-samples/new-feature.js` → `demo-repo/src/loyalty.js`. Commit as `feat: refunds and loyalty statements (#88)`.
2. Build the company knowledge base from Phase 1: `python bugvaccine.py learn --source invoice-kit=antigens.json -o knowledge.json`.
3. List the changed files (`git -C demo-repo diff --name-only main...HEAD`). Launch **one subagent per antigen, in parallel**, checking **only those files** for places its pattern could recur, and merge their mutants into `mutants.pr.json` (`{"antigens": [...], "mutants": [...]}`, ids P1, P2, …).
4. Set the repo up for PR mode: `python bugvaccine.py init demo-repo --name invoice-kit --test "npm test --silent" --force`, then copy `mutants.pr.json` to `demo-repo/.bugvaccine/mutants.json`.
5. Run PR mode exactly as CI would: `python bugvaccine.py pr demo-repo --base main --kb knowledge.json -o results-pr.json`. It runs **two checks** and reports them separately in one comment:
   - **new code vs. company bug history** (should flag `loyalty.js`, which repeats known bugs),
   - **tests vs. past bugs** in the changed files (should flag the untested `refunds.js`).
   Copy `demo-repo/.bugvaccine/pr-comment.md` and `demo-repo/.bugvaccine/results-pr.json` to the project root, and show the comment.
6. Switch back: `git -C demo-repo checkout main`.
7. Optional: write the missing antibody tests on the PR branch and re-run step 5 until the comment shows ✅.
