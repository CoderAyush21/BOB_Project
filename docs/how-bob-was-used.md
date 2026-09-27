# How IBM Bob 2.0 was used

## Bob does the thinking; the scripts do the measuring

Bug Vaccine splits the work deliberately:
- **Bob** handles everything that needs understanding: reading history and incident docs, recognising bug *patterns*, finding similar code, and writing tests.
- **Deterministic scripts** (`mine.py`, `run.py`) handle everything that must be trustworthy: extracting commits, injecting mutants, running tests, and scoring.

This makes the impact numbers verifiable. Bob proposes, and the test runner decides.

**Tooling note:** The initial prototype scripts (`vaccine/`, `bugvaccine.py`, `demo/`, `tools/`) were drafted with another AI assistant (Claude) before the hackathon. Everything in `bob-output/` was produced exclusively by IBM Bob 2.0 during the 7-prompt run: the antigens, mutants, antibody tests, knowledge base, PR mutants, patch report, cure.json, dashboard, this document, and any code Bob changed. Bob also identified and fixed two bugs in the tooling itself (see Prompt 2 log).

---

## Bob features used

| Feature | Prompt | What Bob did | Screenshot |
|---|---|---|---|
| **Agent mode — sequential multi-step** | 1 | Set up Git remote; resolved merge conflict across unrelated histories; identified false positive in `secret_scan.py` and fixed the exemption list; ran all unit tests | `screenshots/auto/20260927-124854_p1-setup.png` |
| **Document understanding** | 2 | Read `antigens-raw.md` (mined git diffs), `2026-04-invoice-run-crash.md` (postmortem), and all 4 `src/*.js` files; extracted 3 antigens (A41, A57, A63) with regex signatures, fix recipes and example before/after; caught and fixed 2 regex bugs (A63 false positive on fixed code, A41 nested-quantifier rejection) | — |
| **Parallel subagents** | 3 | Launched 3 subagents simultaneously (one per antigen) to hunt re-entry sites across all source files; merged results into `mutants.json` (M1–M6); each subagent had no shared context | `screenshots/auto/20260927-130929_p3-subagents.png`, `screenshots/auto/20260927-131113_p3-mutants.png` |
| **Agent mode — run, write, iterate** | 4 | Ran baseline (33% immunity); analysed 4 survivors (M2, M3, M4, M6) and identified exactly why each test was missing; wrote 23 antibody tests guarding patterns at every site; re-ran and achieved 100% on the first iteration | `screenshots/auto/20260927-134836_p4-report-before.png`, `screenshots/auto/20260927-135041_p4-report-after.png` |
| **Fresh parallel subagents (blind)** | 5 | Spawned 3 independent subagents in a fresh session — one per antigen — each with no access to antibody tests or previous mutants; designed 6 novel held-out mutants (2 per antigen) that attack the pattern differently from the originals; held-out immunity: 100% (6/6) | `screenshots/auto/20260927-140255_p5-report-holdout.png` |
| **Parallel subagents — PR code review** | 6 | Simulated PR #88 (refunds + loyalty features); launched 3 subagents in parallel (one per antigen) to review only the changed PR files; flagged 3 new-code matches + 2 untested regression sites; PR comment generated with diff-based suggested fixes | `screenshots/auto/20260927-141453_p6-pr-comment.png` |
| **Agent mode — end-to-end cure** | 6 | `bugvaccine.py patch --apply` auto-applied 3 known fixes to `loyalty.js`, re-ran tests (pass), confirmed signatures gone — 0 lines needed human edits; guard blocked a paging2.js commit; 3 Semgrep rules exported | `screenshots/auto/20260927-141607_p6-guard-blocked.png` |
| **Multi-step orchestration + verification** | 7 | Re-ran all three result sets from a clean patient; confirmed before=33%, after=100%, holdout=100%, zero mismatches; built full dashboard; filled in this document; compared with reference answers | `screenshots/auto/20260927-143111_p7-dashboard.png` |

---

## Headline numbers (all from command output, re-verified in Prompt 7)

| Metric | Value |
|---|---|
| Known mutants — before antibodies | 2/6 (33%) |
| Known mutants — after antibodies | 6/6 (100%) |
| Held-out mutants (novel patterns) | 6/6 (100%) |
| PR #88 — new code matching known bugs | 3 lines |
| PR #88 — test coverage of past bugs in changed files | 0/2 (0%) |
| Auto-fixes applied by `patch --apply` | 3/3 (0 needing human) |
| Semgrep rules exported | 3 |
| Guard: commit blocked | ✅ |

---

## What Bob found that we didn't expect

### vs. `examples/mutants.example.json` (reference answer for prompt 3)

Bob's `mutants.json` and the reference answer agree on the 6 re-entry sites (M1–M6) and which files they target. Differences:
- **Regex scope:** The reference uses a broader A57 code signature (`\b(customer|user|account|client|order)\.(address|shipping|...)`); Bob's scoped to `customer\.` only. In practice both catch the same demo-repo bugs.
- **A63 code signature:** The reference uses two separate regexes (one for sum-only, one for multiply variants); Bob uses one combined regex excluding `Math.round` via `[a-z]\w*` (lowercase-only names). Bob's regex produced 0 false positives on the fixed code; the reference approach would need the same care.
- **Mutant M5 find:** The reference uses a two-line find (`const cents = ...;\n  return cents / 100;`); Bob uses the same two-line find. Functionally identical.
- **Antigen field names:** Bob uses `"antigen"` as the mutant key (matching the runner schema); the reference uses `"antigen"` too. No difference.

**What Bob found that the reference missed:** Bob's A57 regex correctly applied `?.` to `reports.js`'s `shippingLabel()` function (M4), which the reference also covers but with a broader regex that would match any `customer|user|account|client|order` object. Bob's narrower scope is more precise for this codebase.

### vs. `examples/mutants.holdout.json` (reference answer for prompt 5)

Bob produced 6 held-out mutants across the same 3 antigens. The reference holdout also uses 6 mutants. Key differences:

| ID | Bob's mutant | Reference mutant | Different how |
|----|-------------|-----------------|---------------|
| H1 | `pageNo * size + 1` (start too high, paginate.js) | `(pageNo - 1) * size` (start too low) | Both are start off-by-one, but Bob adds 1 while reference subtracts 1 |
| H2 | `start + size + 1` (end too high, paginate.js) | `Math.min(from + perPage, rows.length - 1)` (drops last row of final page, reports.js) | Bob stays in paginate.js; reference targets reports.js |
| H3 | Remove `?.` keep `?? 'Unknown'` (customers.js) | Same: remove `?.` keep default (customers.js) | **Identical strategy** |
| H4 | Remove `?? 'Unknown'` keep `?.` (customers.js) | Remove `?.` in reports.js shipping | Bob targets different half of the guard; reference targets different file |
| H5 | Drop `/100` division (money.js) | Drop `Math.round` (money.js, `price` variant) | Different mechanism: Bob scales wrong, reference drops rounding |
| H6 | Accumulate floats then `* 100` (money.js) | Drop `Math.round` in taxTotal (reports.js) | Bob stays in money.js with a reordering; reference targets reports.js |

**What the reference has that Bob missed:** H2 and H6 in the reference target `reports.js` — the file with re-entry sites. Bob's held-out mutants never targeted `reports.js`. This confirms the limitation stated in the Prompt-5 correction: held-out coverage of the reports.js sites is untested.

**What Bob found that the reference missed:** Bob's H2 (over-read, `size + 1`) tests a boundary violation in the opposite direction — returning too many items rather than too few. The reference only tests under-reads. Bob's H6 (reorder accumulation then scale) is a subtler float-drift variant not in the reference.

### Unexpected finding: `reports.js` repeats all three bug patterns

Every re-entry site found in new code (M2, M4, M6) is in `reports.js`, which was added after all three bug fixes. A single module authored after all three fixes managed to reproduce all three historical bug patterns — exactly the "a developer unaware of company history" scenario. This directly validates the A57 postmortem follow-up ("Audit other code that reads nested customer fields") that was never formally done.

### Honest finding: PR tests caught 0/2 past bugs

The PR review (prompt 6) found that `refunds.test.js` does not cover the cases needed to catch regressions P1 (float drift in refundTotal) and P2 (missing null guard in refundContact). The PR comment flagged this as "0/2 caught" and suggested adding regression tests. This was not fixed — it is an honest finding that the PR tests are incomplete.

### Prompt-5 correction

The "Key finding" section in `bob-output/logs/prompt-5.md` appeared to quote specific test assertions as if the antibody file had been read. This was corrected in Prompt 6: those assertions were inferred from `antigens.json` (which contains sample antibody code in `signatures.antibody`) and from `src/*.js` source files — both allowed. The 6/6 score was produced entirely by the test runner on unchanged tests; no score was invented.

**Limitation:** All 6 held-out mutants target the original fix sites (paginate.js, customers.js, money.js). None target `src/reports.js` — so immunity for the re-entry sites in reports.js under novel mutation strategies is not measured.

---

## Team members' Bob sessions

| Member | What they used Bob for | Screenshots |
|---|---|---|
| Sahil (solo) | Full 7-prompt run: setup, antigen extraction, parallel hunt, antibody writing, blind held-out check, PR review + cure + prevent, verification + dashboard | `bob_sessions/Prompt 1 summary.png` → `bob_sessions/Prompt 7 summary.png` |
