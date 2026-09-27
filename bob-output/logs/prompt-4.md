# Prompt 4 log — Bob prompt 4: re-infect and vaccinate, immunity 33% to 100%

## Bob feature showcased
**Agent mode (run, write, iterate)** — Bob ran the baseline, examined which mutants survived and why, wrote targeted antibody tests, re-ran to verify, and the tests passed on the first iteration without needing a second round.

## What I did

### Step 1: Baseline run

```
M1    KILLED    src/paginate.js  (A41)
M2    SURVIVED  src/reports.js  (A41)
M3    SURVIVED  src/customers.js  (A57)
M4    SURVIVED  src/reports.js  (A57)
M5    KILLED    src/money.js  (A63)
M6    SURVIVED  src/reports.js  (A63)

Immunity: 2/6 (33%)  -> bob-output/results-before.json
```

No INVALID mutants — all 6 find-strings matched exactly once.

### Step 2: Analysis of survived mutants

- **M2** (A41, `reportPage` in `reports.js`): Existing test `reportPage returns rows` checks only that `length > 0`. If `- 1` is added back to the slice end, the test still passes (a shorter result is still > 0). No test verifies that the last element of each page is included.

- **M3** (A57, `billingCity` in `customers.js`): Existing test `returns the billing city` only tests with a valid `{ address: { city: ... } }`. Removing `?.` makes `billingCity({})` crash with `TypeError: Cannot read properties of undefined (reading 'city')` — but no test passes `{}` or `{ address: null }`.

- **M4** (A57, `shippingLabel` in `reports.js`): Existing test `shippingLabel includes name` only tests with `{ name, shipping: { city } }`. Removing `?.` makes `shippingLabel({ name: 'Ada' })` crash — but no test uses a missing/null shipping.

- **M6** (A63, `taxTotal` in `reports.js`): Existing test `taxTotal computes tax` uses `{ amount: 100 }` with `rate: 0.2` → result 20 exactly. Float drift only shows at fractional cent values (e.g. `0.1 * 0.3`). No test uses fractional amounts that would drift.

### Step 3: Write antibodies

Wrote `demo-repo/test/antibodies.test.js` (23 tests) guarding the **pattern** at every function it applies to:

**A41 antibodies** — verify `page()` AND `reportPage()` include the last item of every page:
- Full pages (size 2, size 3), partial last pages, single-item pages
- Each test verifies the exact content of every page (not just length)

**A57 antibodies** — verify `billingCity()` AND `shippingLabel()` survive missing/null/undefined intermediaries:
- `billingCity({})`, `billingCity({ address: null })`, `billingCity({ address: undefined })`
- `shippingLabel({ name })`, `shippingLabel({ name, shipping: null })`, `shippingLabel({ name, shipping: {} })`
- Also tests the happy path (valid address/shipping present)

**A63 antibodies** — verify `invoiceTotal()` AND `taxTotal()` are exact to the cent:
- `0.1 + 0.2 = 0.3` (classic float drift), `0.01 * qty`, `0.33 * 3 = 0.99`
- `taxTotal` with rates 0.1, 0.2, 0.3, 0.5 on fractional amounts
- Sum of 0.01..0.09 = 0.45

All 23 tests passed on the fixed source on first run.

### Step 4: Re-run

```
M1    KILLED    src/paginate.js  (A41)
M2    KILLED    src/reports.js  (A41)
M3    KILLED    src/customers.js  (A57)
M4    KILLED    src/reports.js  (A57)
M5    KILLED    src/money.js  (A63)
M6    KILLED    src/reports.js  (A63)

Immunity: 6/6 (100%)  -> bob-output/results-after.json
```

100% on the first antibody iteration — no second round needed.

### Step 5: Commit and copy

Committed antibodies inside demo-repo: `git -C demo-repo commit -m "test: antibodies for past bugs"` (commit ad676a2).
Copied to `bob-output/antibodies.test.js`.

## Key numbers (from command output)

| Metric | Value |
|---|---|
| Baseline immunity | 2/6 (33%) |
| Mutants survived | 4 (M2, M3, M4, M6) |
| Antibody tests written | 23 |
| Tests passing on fixed source | 23/23 |
| Final immunity | 6/6 (100%) |
| Iterations needed | 1 |
| INVALID mutants | 0 |

## Anything surprising

- First write achieved 100% — no iteration. The strategy of guarding the pattern at every function (not just the exact mutant site) and using boundary values (partial last pages, null/undefined at every level, fractional cents) ensured thorough coverage.
- `taxTotal` float drift: `19.99 * 0.2` = `3.998` in float arithmetic, which rounds to `4.00` — the test verifies this is exactly `4.00` cents (`4.00`). Without integer-cent arithmetic, `Math.round(19.99 * 0.2 * 100) / 100` could drift; the antibody catches this.
