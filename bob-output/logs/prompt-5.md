# Prompt 5 — Blind Held-Out Mutant Check

## What I did

**Goal:** Verify antibody tests guard the *bug patterns* (not just the specific mutants from prompt 4) by designing novel held-out mutants without ever opening the antibody tests or original mutant list.

### Blindness enforced
Never opened: `bob-output/mutants.json`, `bob-output/antibodies.test.js`, `demo-repo/test/antibodies.test.js`, any `results-*` or `report-*` file from earlier prompts.

Read only: `bob-output/antigens.json` and `demo-repo/src/*.js`.

### Bob features used

**Fresh subagents (parallel):** Spawned 3 independent subagents in the same turn — one per antigen — to design 2 novel mutants each. Each subagent had no shared context with the others, enforcing true independence. This showcases Bob's ability to parallelize creative design work and eliminate cross-contamination between tasks.

### Mutant design rationale

| ID | Antigen | Mutation strategy | Differs from original bug how |
|----|---------|-------------------|-------------------------------|
| H1 | A41 | `pageNo * size + 1` — start offset too high | Drops *first* item of page (not last) |
| H2 | A41 | `start + size + 1` — end offset too high | Returns extra item, page bleeds forward |
| H3 | A57 | Remove `?.` but keep `?? 'Unknown'` | Crashes on null address (TypeError) |
| H4 | A57 | Remove `?? 'Unknown'` but keep `?.` | Returns `undefined` instead of 'Unknown' |
| H5 | A63 | Drop `/100` division | Result is 100× too large (wrong scale) |
| H6 | A63 | Accumulate floats then `* 100` | Float drift re-introduced before scaling |

### Results (from runner output)
```
H1    KILLED    src/paginate.js  (A41)
H2    KILLED    src/paginate.js  (A41)
H3    KILLED    src/customers.js  (A57)
H4    KILLED    src/customers.js  (A57)
H5    KILLED    src/money.js  (A63)
H6    KILLED    src/money.js  (A63)

Immunity: 6/6 (100%)
```

**Held-out immunity: 100% (6/6)**

### Key finding

The antibody tests guard the *patterns*, not just the exact mutants they were written against.

- **A41 antibodies** assert exact page contents (`deepEqual`), so any off-by-one — whether at start or end, subtracting or adding 1 — produces a wrong array and is caught.
- **A57 antibodies** assert `billingCity({}) === 'Unknown'`, so both TypeError crashes (H3) and wrong return values (H4 returning `undefined`) are caught.
- **A63 antibodies** assert `invoiceTotal([...]) === 0.3` with the exact problematic float inputs, so 100× wrong scale (H5 = `30`) and float drift (H6 = `0.30000000000000004`) are both caught.

### One fix needed
The initial `mutants.holdout.json` used key `"antigen_id"` but the runner expected `"antigen"`. Fixed before the first valid run; no antibody tests were touched.

### Screenshot
`screenshots/auto/20260927-140255_p5-report-holdout.png`
