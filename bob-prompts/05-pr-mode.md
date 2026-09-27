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
6. **Cure and prevent:**
   - `python bugvaccine.py patch demo-repo --base main --kb knowledge.json --apply --test "npm test --silent" --report patch-report.json`: applies the company's own past fixes to the repeated bugs, re-runs the tests (rolled back if they fail) and re-scans. For any line reported as *needs a human or Bob*, write the fix yourself, then add a `patches` recipe to that antigen so it's automatic next time.
   - Commit the fix, then install the guard: copy `knowledge.json` to `demo-repo/.bugvaccine/company-knowledge.json` and run `python bugvaccine.py guard install demo-repo`. Show that committing a new copy of bug #41 (e.g. `xs.slice(0, 0 + n - 1)`) is **blocked**.
   - Export lint rules for IDEs and CI: `python bugvaccine.py rules --kb knowledge.json -o bug-vaccine.semgrep.yml`.
7. Switch back: `git -C demo-repo checkout main`.
8. Optional: write the missing antibody tests on the PR branch and re-run step 5 until the comment shows ✅.
