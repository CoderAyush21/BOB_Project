# How IBM Bob 2.0 was used

> **Fill this in from your real Bob sessions.** Replace every `TODO` with what actually happened, and link the matching screenshot. Judges will compare this with the screenshots, so only claim what Bob really did.

## Bob does the thinking; the scripts do the measuring

Bug Vaccine splits the work deliberately:
- **Bob** handles everything that needs understanding: reading history and incident docs, recognising bug *patterns*, finding similar code, and writing tests.
- **Deterministic scripts** (`mine.py`, `run.py`) handle everything that must be trustworthy: extracting commits, injecting mutants, running tests, and scoring.

This makes the impact numbers verifiable. Bob proposes, and the test runner decides.

## Bob features used

| Feature | Where | What Bob did | Screenshot |
|---|---|---|---|
| Document understanding | Step 2: antigens | Read git diffs + postmortem; extracted TODO antigens; flagged TODO unfinished follow-ups | `screenshots/TODO` |
| Parallel tasks / subagents | Step 3: hunt | Launched TODO subagents (one per antigen); found TODO re-infection sites | `screenshots/TODO` |
| Agent mode | Steps 4–6 | Ran `run.py`, wrote TODO antibody tests, re-ran TODO times until immunity reached TODO% | `screenshots/TODO` |
| Held-out check | Step 7 | A fresh subagent generated TODO new mutants; held-out immunity TODO% | `screenshots/TODO` |
| PR mode | Step 8 | Parallel subagents checked only the PR's changed files; flagged TODO risks | `screenshots/TODO` |
| Also used to build the project | TODO | e.g. Bob built the GitHub Action wrapper / extended `run.py` | `screenshots/TODO` |

**Be transparent about tooling:** the initial prototype scripts were drafted with another AI assistant (Claude). State that here, and state clearly which parts Bob built or changed.

## What Bob found that we didn't expect

TODO: note anything Bob found beyond `examples/mutants.example.json`, or any mistake it made and how it was corrected. Honest detail here is persuasive.

## Team members' Bob sessions

| Member | What they used Bob for | Screenshots |
|---|---|---|
| TODO | TODO | `screenshots/TODO` |
