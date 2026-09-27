# Prompt 3 log — Bob prompt 3: parallel hunt for re-entry points

## Bob features showcased
**Subagents and parallel tasks** — three independent subagents ran simultaneously, one per antigen, each searching the demo-repo src for every place the antigen's pattern could recur.

## What I did

### Step 1: Fix prompt-2 log
Rewrote `bob-output/logs/prompt-2.md` to fix two problems from the original write:
1. PowerShell here-string escape interpretation corrupted words containing `\r`, `\f`, `\a` (e.g. "return" -> "eturn", "fix_hint" -> "ix_hint", "antibody" -> "ntibody").
2. The dry-run table showed expected substitution results instead of the tool's real printed output, which contained unexpanded group references (`entries\1\2`) because the tool only understood `$1`-style references at that time (not `\1`). Re-ran the dry run after the tool was updated; recorded the real output.

### Step 2: Re-run learn + _check.js dry run
`python bugvaccine.py learn --source invoice-kit=bob-output/antigens.json -o bob-output/knowledge.json`

New output includes a recipe-check line:
```
invoice-kit              3 bug patterns, 3 with debugging signatures
Knowledge base: 3 bug patterns -> bob-output/knowledge.json
Recipe check: 3 bug pattern(s) with fix recipes, each one fixes its own example.
```

### Step 3: Launch parallel subagents

3 subagents launched simultaneously (one per antigen) to hunt re-entry sites. Each was given the antigen definition and all 4 source files as context. Each returned a JSON array of mutant descriptors.

**Bob feature note:** subagents were launched in parallel using `spawn_subagent` with three simultaneous calls in the same turn. This reflects the "parallel tasks, subagents" requirement of the hackathon challenge. Results were collected and merged by the parent agent.

### Step 4: Subagent results

| Subagent | Antigen | Sites found | Notes |
|---|---|---|---|
| 1 | A41 | 2 | paginate.js (original fix), reports.js (written after fix) |
| 2 | A57 | 2 | customers.js (original fix), reports.js (written after fix) |
| 3 | A63 | 2 | money.js (original fix), reports.js (written after fix) |

**Sites in code written AFTER the original fix:**
- M2 — `reportPage()` in `reports.js` uses the same slice pattern as `page()` in `paginate.js`; written after the #41 fix
- M4 — `shippingLabel()` in `reports.js` reads `customer.shipping?.city`; written after the #57 fix (the postmortem's unfinished audit follow-up)
- M6 — `taxTotal()` in `reports.js` uses `Math.round` for money; written after the #63 fix

All 3 new-code sites are in `reports.js`, which was added in the most recent commit ("feat: monthly reports module") long after all three bug fixes.

### Step 5: Merge and validate

Merged into `bob-output/mutants.json` with IDs M1-M6. Validation check:

```
M1 OK  (1) src/paginate.js
M2 OK  (1) src/reports.js
M3 OK  (1) src/customers.js
M4 OK  (1) src/reports.js
M5 OK  (1) src/money.js
M6 OK  (1) src/reports.js

All OK
```

Every `find` string matches exactly once in its file.

## Key numbers

| Metric | Value |
|---|---|
| Subagents launched | 3 (in parallel) |
| Mutants designed | 6 |
| Original fix sites | 3 (one per antigen) |
| New-code sites (written after fix) | 3 (all in reports.js) |
| find-validation failures | 0 |

## Anything surprising

Every re-entry site found in new code is in `reports.js`. This module was added after all three bug fixes and manages to repeat all three historical bug patterns — exactly the scenario that demonstrates Bug Vaccine's value: a developer writing new code after the fixes were shipped, unaware of the company's bug history.

The A57 new-code site (M4) directly validates the postmortem's never-done follow-up: "Audit other code that reads nested customer fields" — `shippingLabel()` does read `customer.shipping?.city` which, if the guard is removed (the mutant), is the exact crash pattern from the SEV-2 incident.
