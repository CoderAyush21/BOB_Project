# Bug Vaccine: prompt for your own repository

> Created by `bugvaccine.py init`. Open **this repository** in IBM Bob (Agent mode) and paste everything below the line.
> Works with other coding agents too. Run the phases in separate sessions if you want one session summary per phase.

---

You are running **Bug Vaccine** on this repository. The goal is to find out which bugs this project has **already fixed** could come back without any test noticing, and then to prevent that.

**Terms:**
- **Antigen**: the reusable *pattern* behind a past bug (not a line number).
- **Mutant**: `{"id","antigen","file","find","replace","why"}`, a small change re-introducing that pattern at one place. `find` must match exactly once in `file`; paths are relative to the repo root.
- **Killed**: tests fail with the mutant applied (good). **Survived**: they pass (the bug could return).
- **Antibody**: a test that guards the *pattern*.

**Principle: you propose, the test runner decides.** Never estimate a number; report only what the commands print. Never change production code except to temporarily apply mutants through the tool. If a feature such as subagents isn't available to you, say so and work sequentially.

The Bug Vaccine command is: `{{BV}}`
The test command for this repo is: `{{TEST}}`
All Bug Vaccine files live in `.bugvaccine/`.

## Phase 1: Antigens (document understanding)
1. `{{BV}} mine .`, then read `.bugvaccine/antigens-raw.md` and every incident/postmortem doc it lists.
2. The miner is deliberately broad, so **discard** commits that aren't behaviour bugs (CI, docs, typing, formatting, dependency bumps). Say how many you discarded.
3. Group the real fixes into antigens. Several fixes often share one pattern; merge them and list all their commits.
4. Write `.bugvaccine/antigens.json`: `{"antigens": [{"id","source_commit","title","pattern","postmortem","unfinished_followups","signatures"}]}`. Aim for the 5–10 most important.
5. **Teach the debugger.** Give each antigen a `signatures` block so the company Debug lab can recognise this bug in future errors, bug reports and code:
   ```json
   "signatures": {
     "lang": "javascript",
     "code":   [{"regex": "what the risky line looks like", "explain": "one line for the developer"}],
     "errors": ["what the error message or bug report looks like"],
     "fix_hint": "how it was fixed, in one sentence",
     "example": {"before": "buggy line", "after": "fixed line"},
     "antibody": "what test guards it"
   }
   ```
   - Regexes must work in **both Python and JavaScript**: no `(?P<name>)`, no inline flags like `(?i)`.
   - `code` regexes run line by line and must **not** match the current, fixed code. Check with `{{BV}} debug --kb <kb> --scan <fixed file>` once the knowledge base is built.
   - `errors` regexes run on the whole text, case-insensitively. Base them on the real error text from the fix commit, issue or postmortem.

## Phase 2: Hunt (parallel subagents)
1. One subagent per antigen, in parallel. Each finds every place in the **current** code where its pattern could recur: the original fix site (it may have moved or been refactored) **and** similar code elsewhere.
2. Write mutants to `.bugvaccine/mutants.json` (`{"antigens": [...], "mutants": [...]}`). Keep each `find` short but unique. Prefer minimal, realistic changes: remove a check, widen a range by one, catch the wrong exception, drop a rounding step.
3. Run `{{BV}} check .` and fix every PROBLEM line until all mutants are valid.

## Phase 3: Measure and vaccinate (Agent mode)
1. `{{BV}} run . --html -o results-before.json`
2. For each survivor, decide: is this a **real** bug a user would notice, or a harmless change (e.g. an error message's wording)? Mark harmless ones as *equivalent*, with a reason. Don't write tests for them.
3. For each real survivor, write antibodies in this repo's normal test style and location. **Guard the pattern:** every affected function, boundaries on both sides, and the invariant the original fix protected. Don't change production code.
4. `{{BV}} run . --html --compare .bugvaccine/results-before.json` and iterate.

## Phase 4: Held-out check (new session or fresh subagent)
Without looking at `mutants.json` or the antibody tests, design 2 new mutants per antigen that differ from simply reverting the fix. Save them as `.bugvaccine/mutants.holdout.json`, then run `{{BV}} check . --mutants .bugvaccine/mutants.holdout.json` and `{{BV}} run . --mutants .bugvaccine/mutants.holdout.json -o results-holdout.json`. Report the score as it is, and don't tune the antibodies afterwards.

## Report
A table of antigens → mutants → caught/survived/equivalent; immunity before → after; held-out immunity; the antibody tests added; and any real test gaps found. Recommend a `min_immunity` value for `.bugvaccine/config.json` if the team wants a CI gate.
