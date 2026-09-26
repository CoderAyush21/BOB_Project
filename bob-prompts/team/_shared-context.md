# Shared context for every Bug Vaccine phase (IBM Bob: read this first)

## The hackathon
We're entering the **IBM Bob 2.0 Hackathon** (lablab.ai). The challenge is to build, *using IBM Bob 2.0*, a working prototype that improves a developer workflow, using Agent mode, parallel tasks, subagents and document understanding to manage **multiple steps, not just assist with coding**, and to demonstrate measurable impact.
Judging: Application of Technology · Business Value · Originality · Presentation.

The team splits the work: **each member runs one phase in their own Bob session.** You are running exactly one phase. Don't do other phases' work.

## The product: Bug Vaccine
Teams fix bugs, but fixes often ship without regression tests, and the same mistakes get rewritten in new code. Bug Vaccine turns a repo's git history and postmortems into a vaccine:

- **Antigen**: the reusable *pattern* behind a past bug (e.g. "summing currency as floats instead of integer cents"), not a line number.
- **Mutant**: one small code change that re-introduces an antigen at a specific place: `{"id","antigen","file","find","replace","why"}`. `find` must match **exactly once** in the file.
- **Killed / caught**: tests fail with the mutant applied (good). **Survived**: tests still pass (the old bug could return unnoticed).
- **Immunity**: caught ÷ valid mutants.
- **Antibody**: a test that guards an antigen's *pattern*.

| Phase | Name | Bob feature showcased |
|---|---|---|
| 1 | Extract antigens | Document understanding |
| 2 | Hunt re-infection sites | Parallel subagents |
| 3 | Re-infect and vaccinate | Agent mode |
| 4 | Held-out check | Fresh subagent (blind test) |
| 5 | PR mode | Subagents + code review workflow |
| 6 | Write-up and verification | Multi-step orchestration |

**Core principle: you propose, the test runner decides.** You do the understanding; the scripts do the measuring. Never estimate, round or invent a number. Every figure must come from a script's output.

## Repository map
| Path | What | Access |
|---|---|---|
| `tools/setup_phase.py` | Prepares this machine for your phase | ✅ run first |
| `demo/build_demo_repo.py` | Builds `demo-repo/` (invoicing library, 3 bug fixes + 1 postmortem) | ✅ |
| `vaccine/mine.py`, `vaccine/run.py` | Mining; injecting, scoring and reporting | ✅ run |
| `tools/screenshot.ps1` | Evidence screenshots | ✅ run |
| `bob-output/` | **Team handoff folder**: earlier phases' outputs; you add yours here | ✅ read what your phase lists; write your outputs |
| `docs/` | Submission docs | ✅ read; only Phase 6 edits them |
| `examples/`, `prototype/`, `prototype-output/` | **Reference answers** | ❌ **never open** (exceptions are named explicitly in Phases 5 and 6) |

`demo-repo/` is git-ignored and rebuilt by `setup_phase.py` on every machine. Never change `demo-repo/src/` unless your phase says so.

## Rules
1. **Honesty.** If a Bob feature (subagents, parallel tasks) isn't available to you, say so and work sequentially. Never claim a feature you didn't use. Report scores exactly, including bad ones.
2. **No secrets.** Never write, request or print API keys, passwords or IBM Cloud credentials. Leaked IBM Cloud keys can get accounts suspended.
3. **Windows / PowerShell:** use `;` not `&&`; Python is `python`.
4. **Screenshots (you take these):** at each 📸, run
   `powershell -ExecutionPolicy Bypass -File tools/screenshot.ps1 -Name p<PHASE>-<MEMBER>-<what>`
   Add `-Html <file.html>` to capture a report. Before the first screen capture, ask the member to close private windows (email, chats, password managers) and wait for their OK.
5. **Log:** at the end, write `bob-output/logs/phase-<PHASE>-<MEMBER>.md` with: what you did, the Bob features you **actually** used and how, the key numbers (copied from script output), surprises, and any mistake you made and how you fixed it.
6. **Finish** with a summary: files created, screenshots taken, key numbers. Then stage and commit **only** your phase's files (`git add bob-output screenshots; git commit -m "Phase <PHASE> (<MEMBER>): <summary>"`). **Don't push:** the member checks and pushes. Last, tell the member:
   `✅ Phase <PHASE> done. Please (1) screenshot my task session summary → screenshots/manual/phase-<PHASE>-<MEMBER>-summary.png, (2) git add it and push, (3) tell the next person.`
