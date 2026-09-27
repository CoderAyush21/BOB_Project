# Prompt 7 — Verified Results, Dashboard and Write-up

## What I did

### Step 1: Honesty correction committed (session summary)
Committed `bob_sessions/Prompt 6 summary.png` as the start-of-prompt step.

### Step 2: Re-verification (all numbers re-run from scratch)

Rebuilt a clean patient (`python demo/build_demo_repo.py`), then re-ran all three result sets:

```
BEFORE  verify:
M1    KILLED    src/paginate.js  (A41)
M2    SURVIVED  src/reports.js  (A41)
M3    SURVIVED  src/customers.js  (A57)
M4    SURVIVED  src/reports.js  (A57)
M5    KILLED    src/money.js  (A63)
M6    SURVIVED  src/reports.js  (A63)
Immunity: 2/6 (33%)

AFTER  verify:
M1    KILLED    M2    KILLED    M3    KILLED
M4    KILLED    M5    KILLED    M6    KILLED
Immunity: 6/6 (100%)

HOLDOUT  verify:
H1    KILLED    H2    KILLED    H3    KILLED
H4    KILLED    H5    KILLED    H6    KILLED
Immunity: 6/6 (100%)
```

**Comparison with saved results:**
```
BEFORE  saved=2/6(33%) verify=2/6(33%) match=True
AFTER   saved=6/6(100%) verify=6/6(100%) match=True
HOLDOUT saved=6/6(100%) verify=6/6(100%) match=True
All per-mutant statuses match.
```

**Zero mismatches.** All headline numbers verified.

### Step 3: Dashboard
Built RAG index (11 chunks: 3 fix, 3 pattern, 5 postmortem) and full dashboard.
Screenshot: `screenshots/auto/20260927-143111_p7-dashboard.png`

### Step 4: docs/how-bob-was-used.md
Replaced all TODOs with real session data:
- Features table: 8 rows covering all 7 prompts with real screenshot filenames
- Headline numbers table: all from command output
- Reference comparison: detailed diff vs `examples/mutants.example.json` and `examples/mutants.holdout.json`
- Honest findings: PR 0/2 immunity, Prompt-5 correction, held-out limitation

### Step 5: Reference comparison
Opened `examples/mutants.example.json` and `examples/mutants.holdout.json` for the first time.

**vs. mutants.example.json:** Bob and reference agree on all 6 re-entry sites (M1–M6) and target files. Main differences: Bob uses narrower A57 regex (customer-only), and Bob uses `"antigen"` key (runner schema). Bob's A63 regex avoids false positives via lowercase check; reference uses two separate patterns.

**vs. mutants.holdout.json:**
- H1: Bob adds +1 to start; reference subtracts 1 (both start off-by-one)
- H2: Bob over-reads in paginate.js; reference drops last row of final page in reports.js
- H3: Identical strategy (remove `?.` in customers.js)
- H4: Bob removes `??` default; reference removes `?.` in reports.js
- H5: Bob drops `/100`; reference drops `Math.round`
- H6: Bob reorders accumulation in money.js; reference drops rounding in reports.js (taxTotal)

**What reference has that Bob missed:** H2 and H6 in reference target reports.js — Bob's held-out set never covered the reports.js re-entry sites.
**What Bob has that reference missed:** Bob's H2 (over-read) tests the opposite boundary direction. Bob's H6 (reorder-then-scale) is a subtler float-drift variant.

### Step 6: Number corrections
Two mismatches found between README/docs and Bob's real results. Changes made with user approval:
- README.md: "6 Semgrep rules" → "3 Semgrep rules" (3 antigens × 1 pattern each)
- docs/problem-and-solution.md: "6 antibody tests" → "23 antibody tests" (Bob wrote 23 test() calls)

### Step 7: bob-output/README.md
Written: one-paragraph intro (dated 27 September 2026) + table of all 21 files with descriptions.

### Step 8: bob_sessions/ check
Present: Prompt 1–6 summary.png (6 files). **Missing: Prompt 7 summary.png** — expected until the session is saved.

## Bob features used
**Multi-step orchestration:** Agent mode ran 8 sequential steps with real command output at each step — rebuild, re-run three sets of tests, compare results, build dashboard, fill docs, compare with reference, fix numbers, write README, verify sessions. No step was skipped or estimated.

## Key numbers (all from command output, re-verified)

| Metric | Value |
|---|---|
| Verified before immunity | 2/6 (33%) — matches saved |
| Verified after immunity | 6/6 (100%) — matches saved |
| Verified holdout immunity | 6/6 (100%) — matches saved |
| Per-mutant mismatches | 0 |
| RAG index chunks | 11 (3 fix, 3 pattern, 5 postmortem) |
| README/docs corrections | 2 (Semgrep rules 6→3; antibody tests 6→23) |
| bob_sessions summaries present | 6/7 (Prompt 7 missing — expected) |
