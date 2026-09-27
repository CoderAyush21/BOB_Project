# Prompt 6: Code review, cure and prevent

---

You are running **Prompt 6 of 7** of the Bug Vaccine hackathon run. **Bob features showcased: parallel subagents in the code review workflow, and Agent mode fixing bugs end to end.**

1. Read `bob-prompts/hackathon/_context.md` and follow it. N = 6. Do its "start of every prompt" step.
2. If `demo-repo/` is missing: `python demo/build_demo_repo.py`, copy `bob-output/antibodies.test.js` to `demo-repo/test/`, and commit it inside `demo-repo`.
3. **Simulate a pull request.** `git -C demo-repo checkout -b feature/refunds`. Copy **only** these files from `examples/`: `examples/pr-refunds/src/refunds.js` → `demo-repo/src/refunds.js`, `examples/pr-refunds/test/refunds.test.js` → `demo-repo/test/refunds.test.js`, and `examples/debug-samples/new-feature.js` → `demo-repo/src/loyalty.js`. Commit inside `demo-repo` as `feat: refunds and loyalty statements (#88)`.
4. **Hunt in the PR, in parallel:** list the changed files (`git -C demo-repo diff --name-only main...HEAD`), launch **one subagent per antigen** checking only those files, and merge their mutants into `bob-output/mutants.pr.json` (ids P1, P2, …).
5. **Review it as CI would:**
   - `python bugvaccine.py init demo-repo --name invoice-kit --test "npm test --silent" --force`, then copy `bob-output/mutants.pr.json` to `demo-repo/.bugvaccine/mutants.json`.
   - `python bugvaccine.py pr demo-repo --base main --kb bob-output/knowledge.json -o results-pr.json`
   - Copy `demo-repo/.bugvaccine/pr-comment.md` and `demo-repo/.bugvaccine/results-pr.json` to `bob-output/`. Show the comment: it reports **new code vs. company bug history** and **tests vs. past bugs** separately, with a suggested fix for each repeated bug.
   - 📸 `-Name p6-pr-comment` with `bob-output/pr-comment.md` open.
6. **Cure:** `python bugvaccine.py patch demo-repo --base main --kb bob-output/knowledge.json --apply --test "npm test --silent" --report bob-output/patch-report.json`. It applies the team's own past fixes, re-runs the tests (rolled back if they fail) and re-scans. For any line reported as *needs a human or Bob*, write the fix yourself and add a `patches` recipe to that antigen in `bob-output/antigens.json`. Commit inside `demo-repo`: `fix: apply the team's known fixes`.
7. **Re-check:** `python bugvaccine.py pr demo-repo --base main --kb bob-output/knowledge.json -o results-pr-after.json` and report how many repeated bugs remain.
8. **Prevent:**
   - Copy `bob-output/knowledge.json` to `demo-repo/.bugvaccine/company-knowledge.json`, then `python bugvaccine.py guard install demo-repo`.
   - Prove it: write `export const firstPage = (xs, n) => xs.slice(0, 0 + n - 1);` to `demo-repo/src/paging2.js`, `git -C demo-repo add -A`, and `git -C demo-repo commit -m "feat: paging helper"`. The commit must be **blocked**. 📸 `-Name p6-guard-blocked` showing it.
   - Clean up: `git -C demo-repo reset -q HEAD src/paging2.js`, delete `demo-repo/src/paging2.js`, `python bugvaccine.py guard uninstall demo-repo`.
   - `python bugvaccine.py rules --kb bob-output/knowledge.json -o bob-output/bug-vaccine.semgrep.yml`
9. Write `bob-output/cure.json` for the dashboard, using real values from the commands above:
   `{"patch": <contents of bob-output/patch-report.json>, "pr_after": {"new_code": <repeated bugs after the patch>, "untested": <total - killed from results-pr-after.json>, "total": <total>}, "guard": {"blocked": true|false, "file": "src/paging2.js", "line": "<the line you tried>", "output": "<the guard's message>"}, "rules": {"count": <number of rules written>, "file": "bug-vaccine.semgrep.yml"}}`
10. `git -C demo-repo checkout main`
11. Finish with the end-of-prompt steps in `_context.md` (commit "Bob prompt 6: PR review, cure and prevent").
