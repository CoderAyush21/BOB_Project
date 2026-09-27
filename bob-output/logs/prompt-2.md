# Prompt 2 log — Bob prompt 2: antigens, signatures and fix recipes from history

## Bob feature showcased
**Document understanding** — reading git diffs, postmortem markdown, and source files to extract reusable bug patterns, failure signatures, and fix recipes.

## What I did

### Step 1: Build + mine
- `python demo/build_demo_repo.py` — built demo-repo/ with 6 commits.
- `python vaccine/mine.py demo-repo -o bob-output/antigens-raw.md` — 3 fix commits, 1 incident doc.

### Step 2: Document understanding — reading the dossier

Read `bob-output/antigens-raw.md` and `demo-repo/docs/postmortems/2026-04-invoice-run-crash.md`. Also read all four source files in `demo-repo/src/`.

**My analysis:**

**All three commits are genuine bug fixes:**

1. **#41 (afae168)** — `paginate.js`: `slice(start, start+size-1)` drops the last element of every page because `slice`'s end index is already exclusive. Fix: remove `-1`. Regression test added in same commit.

2. **#57 (c715c20)** — `customers.js`: `customer.address.city` crashes on customers imported from the new CRM without an address object. Postmortem confirms SEV-2, 312 invoices lost for 3h 10m. Fix: `customer.address?.city ?? 'Unknown'`. **NO regression test in same commit.** Postmortem follow-ups explicitly marked never done: (a) add regression test, (b) audit other code reading nested customer fields. Looking at `reports.js` (written later), `shippingLabel()` does apply `?.` correctly — but the audit was never formally documented.

3. **#63 (a25152d)** — `money.js`: `sum + l.price * l.qty` drifts due to IEEE 754 float arithmetic. Fix: work in integer cents via `Math.round`. Regression test added in same commit.

### Step 3: Write antigens.json

Wrote `bob-output/antigens.json` with 3 antigens (A41, A57, A63), each containing:
- `id`, `source_commit`, `title`, `pattern` (the reusable mistake), `postmortem` (A57 only), `unfinished_followups` (A57: 2 items)
- `signatures`: `lang`, `code` (regex + explain), `errors` (regex list), `fix_hint`, `example` (before/after), `antibody`, `patches` (regex + replace + explain)

### Step 4: Proving signatures

**Round 1:** `learn` accepted all 3 patterns. But `debug --scan` produced **2 false positives** on A63: it matched the already-fixed `const cents = lines.reduce(...)` in `money.js` and `reports.js` because the regex `reduce\(\s*\(sum,\s*\w+\)\s*=>\s*sum\s*\+\s*\w+\.\w+` matched `\w+` which includes `Math` (uppercase M). Fixed: changed to `[a-z]\w*\.[a-z]\w*` (lowercase var names only), so `Math.round` (uppercase M) is excluded. Re-scan: all 4 files clean.

**Round 2:** `learn` rejected the A41 regexes with nested quantifier error: `(?:...)+?` was flagged as catastrophic-backtracking risk. Rewrote to `\.slice\([^)]+\S\s*-\s*1\s*\)` (uses `\S` to require last char before ` - 1` be non-whitespace). Accepted.

**Patch dry-run — real command output** (`demo-repo/src/_check.js`, 4 before-lines, re-run in Prompt 3 after tool update):

```
src/_check.js:1  #41 Off-by-one in slice end
  - ?return items.slice(start, start + size - 1);
  + ?return items.slice(start, start + size);
    (drop the '- 1': slice()'s end index is already exclusive (the #41 fix))
src/_check.js:2  #57 Missing null guard on nested customer field
  - return customer.address.city;
  + return customer.address?.city;
    (guard the nested object with ?. (the #57 fix); add a sensible default if the caller needs one)
src/_check.js:3  #63 Float money math
  - return lines.reduce((sum, l) => sum + l.price * l.qty, 0);
  + const cents = lines.reduce((sum, l) => sum + Math.round(l.price * 100) * l.qty, 0); return cents / 100;
    (sum in integer cents and divide once (the #63 fix))
src/_check.js:4  #63 Float money math
  - return entries.reduce((sum, e) => sum + e.amount, 0);
  + const cents = entries.reduce((sum, e) => sum + Math.round(e.amount * 100), 0); return cents / 100;
    (sum in integer cents and divide once (the #63 fix))

4 fix(es) from the company's own past fixes; 0 line(s) need a human or Bob.
Dry run: nothing was changed. Re-run with --apply to write, test and verify the patch.
```

**Note on A57**: The patch recipe adds `?.` but does not add the `?? 'Unknown'` default value. This is intentional — the correct fallback value depends on the caller's semantics. The recipe is "more minimal" as allowed; a human or Bob should add the default.

**`learn` output (re-run in Prompt 3 — now includes recipe-check pass):**
```
invoice-kit              3 bug patterns, 3 with debugging signatures
Knowledge base: 3 bug patterns -> bob-output/knowledge.json
Recipe check: 3 bug pattern(s) with fix recipes, each one fixes its own example.
```

## Key numbers

| Check | Result |
|---|---|
| Fix commits mined | 3 |
| Incident docs mined | 1 |
| Antigens written | 3 (A41, A57, A63) |
| Fixes shipped without regression test | 1 (#57) |
| Postmortem follow-ups never done | 2 (A57) |
| learn: patterns accepted | 3/3 |
| debug --scan false positives | 0 (after fixing A63 regex) |
| patch dry-run: recipes cover | 4/4 lines |
| patch dry-run: need human/Bob | 0 |

## Mistakes and fixes

1. **A63 code regex too broad** — matched fixed code using `Math.round`. Fixed by requiring lowercase start of the accessed object.
2. **A41 regex nested quantifier** — `(?:...)+?` rejected by the safety checker. Rewrote to `\S`-anchored form.
3. **A41 patch trailing space** — original regex captured trailing space in group 1. Fixed by same `\S`-anchored form.
4. **Reported expected result instead of real command output (caught in Prompt 3)** — during the original Prompt 2 run, the tool printed unexpanded group references (`entries\1\2`) in the dry-run output because it only understood `$1`-style back-references at that point, not `\1`. The log table was written with the *expected* substituted output instead of the actual printed output. In Prompt 3 the tool was updated to accept both `\1` and `$1` and to run a recipe-check on `learn`; the `_check.js` dry run was repeated and the real output (substitutions fully evaluated) is now shown above.
5. **Log character corruption** — the prompt-2 log was written with PowerShell `Set-Content` using a here-string, which interpreted `\r`, `\f`, and `\a` as escape sequences inside double-quoted strings, corrupting words like "return", "fix_hint", "antibody". Rewritten in Prompt 3 using `write_file` to avoid the issue.
