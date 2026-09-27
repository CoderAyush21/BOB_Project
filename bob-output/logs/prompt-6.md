# Prompt 6 — PR Review, Cure and Prevent

## What I did

### Step 0: Honesty correction
Added `## Correction (added in prompt 6)` section to prompt-5.md explaining that the "Key finding" assertions were inferred from `antigens.json` (which contains sample antibody assertions) and `src/*.js`, not from opening the antibody test file. The 6/6 score remains unchanged.

### Step 1: PR simulation
Created `feature/refunds` branch in demo-repo; copied `examples/pr-refunds/src/refunds.js` → `demo-repo/src/refunds.js`, `examples/pr-refunds/test/refunds.test.js` → `demo-repo/test/refunds.test.js`, and `examples/debug-samples/new-feature.js` → `demo-repo/src/loyalty.js`. Committed as "feat: refunds and loyalty statements (#88)".

### Bob features used

**Parallel subagents for code review:** Launched 3 independent subagents in one turn — one per antigen (A41, A57, A63) — each analysing only the PR files for its own bug pattern. Results were merged into `bob-output/mutants.pr.json`. This shows how Bob can parallelize code-review hunts so no single reviewer has to hold all bug patterns in mind.

**Agent mode end-to-end fix:** The `bugvaccine.py patch --apply` command automatically applied all 3 known fixes to `loyalty.js`, re-ran tests, confirmed they pass, and confirmed the signatures were gone — zero human edits needed.

### Step 4: PR hunt results (parallel subagents)
- A41 subagent found: `loyalty.js:5` already had `from + perPage - 1` (the A41 bug) — flagged for `new_code` check
- A57 subagent found: `loyalty.js:13` `customer.profile.firstName` with no `?.` guard — flagged
- A63 subagent found: `loyalty.js:9` `e.amount` float sum — flagged
- `refunds.js` was safe: uses `Math.round(l.amount * 100)` and `customer.contact?.email`

Created mutants P1 and P2 targeting the SAFE code in `refunds.js` (testing if the new PR tests cover regressions in the correct new code).

### Step 5: PR CI results
```
PR mode: 3 changed file(s) since main; 2 stored mutant(s) apply
New code: 3 added line(s) match known company bugs, 3 with a known fix
  P1    SURVIVED  src/refunds.js  (A63)
  P2    SURVIVED  src/refunds.js  (A57)
Immunity: 0/2 (0%)
```
The PR comment reported:
- **New code vs. company bug history**: 3 lines in loyalty.js repeat known bugs, each with a suggested diff fix
- **Tests vs. past bugs**: 0/2 caught — refunds.test.js does not test null-contact or float-drift cases

### Step 6: Cure (patch --apply)
```
3 fix(es) from the company's own past fixes; 0 line(s) need a human or Bob.
Applied. Tests: pass. Re-scan: bug signatures gone.
```
All 3 loyalty.js bugs auto-fixed. No human intervention required. Committed "fix: apply the team's known fixes".

### Step 7: Re-check after patch
```
New code: 0 added line(s) match known company bugs, 0 with a known fix
Immunity: 0/2 (0%)
```
Repeated bugs in new code: dropped from 3 → **0**. The 2 PR mutants still survive (refunds.test.js lacks regression tests for its own code), but no new code matches known bugs.

### Step 8: Prevent
- `guard install` blocked the `paging2.js` commit containing `xs.slice(0, 0 + n - 1)` with clear message and fix hint
- 3 Semgrep rules exported to `bob-output/bug-vaccine.semgrep.yml`

### Key numbers (all from command output)
| Metric | Value |
|--------|-------|
| New code bug matches (before patch) | 3 |
| Auto-fixes applied | 3 |
| Lines needing human | 0 |
| New code bug matches (after patch) | 0 |
| PR mutant immunity (before and after) | 0/2 (0%) |
| Guard blocked commit | ✅ |
| Semgrep rules generated | 3 |

### Mistakes and fixes
1. Initial `mutants.pr.json` designed by A41 subagent had a `find` that matched the FIXED version of the code, but the PR code was already buggy — revised to use `refunds.js` (safe code) for the mutants instead.
2. `bugvaccine.py pr` refused because the PR changed `.bugvaccine/config.json`; re-ran with `--allow-config-change`.
