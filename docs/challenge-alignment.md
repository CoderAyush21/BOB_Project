# Challenge alignment checklist

How Bug Vaccine meets each part of the IBM Bob 2.0 Hackathon brief. Tick these off before submitting.

## The brief

| Brief says | How Bug Vaccine meets it | Status |
|---|---|---|
| "Improves a specific developer workflow: … debugging, code review, **testing**, **application maintenance**…" | Regression-risk management: stopping old bugs from coming back. It covers testing + maintenance, and feeds code review (run it on a PR). | ✅ |
| "Clearly defining a problem where time, effort, or errors are too high" | Fixes ship without regression tests, and the same bug patterns get rewritten in new code. See `problem-and-solution.md`. | ✅ |
| "Using IBM Bob 2.0, build a working prototype on a real or sample project" | Sample project: `demo/build_demo_repo.py`. Prototype: `prototype/run_prototype.py`. **Bob must produce the AI steps live**; see "Must do in Bob" below. | ⚠️ needs Bob run |
| "Demonstrates a **full solution**" | The loop is complete: mine → antigens → hunt → re-infect → antibodies → prove. | ✅ |
| "Agent mode" | Steps 3 and 5: Bob runs `run.py`, writes tests, re-runs, and iterates until 100%. | ⚠️ show in video |
| "Parallel tasks, subagents" | Step 3: one subagent per antigen, hunting in parallel. | ⚠️ show in video |
| "Document understanding" | Step 2: Bob reads git diffs **and postmortem docs**, and flags unfinished follow-ups (e.g. "add a regression test ← never done"). | ⚠️ show in video |
| "Manage and improve multiple steps, not just assist with coding" | Bob drives a 6-step workflow end to end. It isn't only writing code. | ✅ |
| "Clearly demonstrate impact" | Measured, not estimated: immunity 33% → 100% on known mutants, a held-out check against overfitting, and 5 risks flagged in PR #88 before merge (3 new lines repeating known bugs, 2 untested past-bug sites). | ✅ |
| "Code review" workflow | PR mode: `bugvaccine.py pr` checks new lines against company bug history *and* re-runs stored mutants in changed files, in one PR comment. | ✅ |

## Judging criteria

| Criterion | Evidence to show judges |
|---|---|
| **Application of Technology** | Screen-record Bob's subagents running in parallel, Agent mode running `run.py`, and Bob reading the postmortem. Name each feature out loud. |
| **Business Value** | Regressions are some of the most expensive bugs: already paid for once, then shipped again. The #57 postmortem shows the cost (SEV-2, 3h outage, 312 invoices delayed) and that its follow-up was never done. |
| **Originality** | Not generic mutation testing, which produces thousands of random mutants. It injects only **your own past bugs**. See the README section "How it's different". **Don't claim "never been done."** Related research exists (Tufano et al., *Learning How to Mutate Source Code from Bug-Fixes*, ICSME 2019; Meta's 2025 work on LLM mutation-guided test generation). Verify these and cite them. Our angle: a per-repo tool that turns **your own incidents and postmortems** into tests, run by an agent, and built into code review. |
| **Presentation** | 3-minute video (`demo-video-script.md`) and the before/after report as the visual payoff. |

## Deliverables (from the brief)

- [ ] Video demonstration → `demo-video-script.md`
- [ ] Written problem and solution statement → `problem-and-solution.md`
- [ ] Written statement on how IBM Bob was used → `how-bob-was-used.md` (fill in after the Bob run)
- [ ] Code repository **built from the IBM hackathon repo template**
- [ ] IBM Bob task session summary screenshots → `screenshots/`, from **every team member**
- [ ] Publicly accessible repo link
- [ ] **No IBM Cloud credentials in the repo.** Check with `git grep -i -E "apikey|api_key|password|secret"` before pushing.

## Must do in Bob (the prototype uses stand-ins for these)

The prototype fills the three `[BOB]` steps with pre-written outputs so you can see the flow. For the submission, **Bob has to produce them live**:

1. `bob-prompts/01-extract-antigens.md` → `antigens.json`
2. `bob-prompts/02-design-mutants.md` → `mutants.json` (parallel subagents)
3. `bob-prompts/03-vaccinate.md` → antibody tests + report
4. `bob-prompts/04-holdout.md` → held-out score (fresh subagent; report the number honestly, whatever it is)
5. `bob-prompts/05-pr-mode.md` → PR comment

Also use Bob to **build or extend part of the tooling** (e.g. a GitHub Action wrapper for PR mode) and screenshot it. The current scripts were written with another AI assistant, so say so in `how-bob-was-used.md` rather than implying Bob wrote them.

## Fixed after the mock judge review

| Issue | Fix |
|---|---|
| Stand-ins instead of Bob | Still open. Must be done in Bob (see above). |
| 33% is by construction | Still open. Stretch goal: run on a real repo (below). |
| 100% "after" score is circular | Held-out mutants (`examples/mutants.holdout.json`, `bob-prompts/04-holdout.md`). The prototype first scored 50%, which led to the pattern-level antibody rule. |
| "Never been done" claim | Positioning revised, with related work named above. |
| Misleading "~8s full check" | Now "~4.5 s per re-check with `node --test`" (measured; ~11 s through `npm test`). |
| Postmortem follow-ups 0/1 vs 2 listed | Corrected to 0/2 → 2/2. |
| CRLF files break multi-line mutants | `apply_mutant` converts line endings; unit-tested. |
| Timeouts silently counted as caught | Separate `timeout` status, shown in console, report and JSON. |
| Fix detection only reads subjects | Full message; `resolves/closes #n`, reverts, `fix(scope):`; incident docs collected. |
| Report not visible without running | Screenshot committed at `docs/img/report.png`. |
| No LICENSE | MIT `LICENSE` added. |
| Tool had no tests | `tests/`: unit, end-to-end, security and company dry-run regression tests; CI on Python 3.9-3.13 x 3 OSes. |
| Report not verifiable | Each row links its fix commit and postmortem, and shows the injected diff. |
| `shell=True` | Documented in `run.py`: only pass trusted test commands. |

Afterwards, compare Bob's `mutants.json` with `examples/mutants.example.json`. If Bob finds extra sites, even better: say so in the video.

## Recommended stretch goal (big boost for "real project")

After the demo repo, run Bug Vaccine on **one real open-source repo** with a test suite and a history of `fix:` commits. `run.py` accepts any test command (`--test "pytest -q"`, `--test "npm test"`, …). Even one real finding ("this repo's fix for issue #X has no test and the bug can silently return") is very persuasive.
