# Prompt 4 — Held-out check (Bob, NEW subagent)

> Screenshot the session summary → `screenshots/`.
> Run this only **after** prompt 3 is finished and the antibodies are committed.

---

Launch a **fresh subagent** that has NOT seen `mutants.json`, `demo-repo/test/antibodies.test.js`, or any earlier conversation.

Give it only `antigens.json` and read access to `demo-repo/src/`. Its task:

> For each antigen, design 2 NEW ways to re-introduce that same bug pattern into the current code. Each must be a different change from the obvious "revert the fix": e.g. an off-by-one at the start instead of the end, a guard removed while the default is kept, a rounding step dropped. Use the same JSON mutant format with `find` (exactly one match), `replace` and `why`. Use ids H1, H2, …

Save the result as `mutants.holdout.json`, then run:

`python vaccine/run.py mutants.holdout.json --repo demo-repo -o results-holdout.json --label "held-out mutants" --html report-holdout.html`

**Do not change the antibodies based on this result.** It is the honest measure of whether they generalise. Report the score as it is. If some held-out mutants survive, list them as known gaps.
