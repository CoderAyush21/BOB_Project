# Team run: one phase per person

Each team member runs **one phase** in **their own IBM Bob session** and saves their own session-summary screenshot. That meets the hackathon requirement for screenshots from every team member.

## Order: who waits for whom

```
Phase 1 ─┬─► Phase 2 ─► Phase 3 ─► Phase 4 ─┐
(antigens)│  (hunt)     (vaccinate) (held-out)├─► Phase 6
          └─► Phase 5 ───────────────────────┘   (write-up)
              (PR mode, can run in parallel with 2–4)
```

`tools/setup_phase.py` refuses to start a phase if an earlier phase's output hasn't been pushed yet, and tells you who you're waiting for.

## Who does what

| Team size | Assignment |
|---|---|
| **6** | One phase each: 1, 2, 3, 4, 5, 6 |
| **5** | A: 1 · B: 2 · C: 3 · D: 4 · E: 5 + 6 |
| **4** | A: 1 + 6 · B: 2 + 3 · C: 4 · D: 5 |
| **3** | A: 1 + 5 · B: 2 + 3 · C: 4 + 6 |
| **2** | A: 1 + 2 + 3 · B: 4 + 5 + 6 |

**Always** give Phase 4 (held-out check) to someone who did **not** run Phase 2 or 3, and use a brand-new Bob session. That's what makes the blind test genuinely blind, and it's the answer to a judge asking "isn't your 100% circular?"

If one person runs two phases, use a **new Bob session for each phase**, so each gets its own session summary screenshot.

## What each person does (about 20–40 minutes)

1. `git pull` the team repo.
2. Close private windows (email, chats, password managers), because Bob takes screen captures.
3. Open the `bug-vaccine/` folder in IBM Bob, in Agent mode.
4. Open your phase file below, replace `<MEMBER>` with your first name, and paste everything below its line into Bob.
5. When Bob finishes, take a screenshot of **Bob's task session summary** (Win+Shift+S) and save it as `screenshots/manual/phase-<N>-<name>-summary.png`. Bob can't take this one itself.
6. Check what Bob committed, `git add` your summary screenshot, `git commit`, `git push`.
7. Tell the next person.

| Phase | File | Needs | Bob feature |
|---|---|---|---|
| 1 | [phase-1-antigens.md](phase-1-antigens.md) | — | Document understanding |
| 2 | [phase-2-hunt.md](phase-2-hunt.md) | 1 | Parallel subagents |
| 3 | [phase-3-vaccinate.md](phase-3-vaccinate.md) | 1, 2 | Agent mode |
| 4 | [phase-4-holdout.md](phase-4-holdout.md) | 1, 3 | Fresh subagent (blind test) |
| 5 | [phase-5-pr-mode.md](phase-5-pr-mode.md) | 1 | Subagents + code review |
| 6 | [phase-6-writeup.md](phase-6-writeup.md) | 1–5 | Orchestration + verification |

Every phase first reads [`_shared-context.md`](_shared-context.md), so each Bob session understands the whole project, not just its own step.

## Where things go

| What | Where | Made by |
|---|---|---|
| Bob's work (antigens, mutants, antibodies, results, reports, PR comment) | `bob-output/` | Bob |
| Each phase's log | `bob-output/logs/phase-<N>-<name>.md` | Bob |
| Progress screenshots | `screenshots/auto/p<N>-<name>-*.png` | Bob, via `tools/screenshot.ps1` |
| **Session summary screenshots (required)** | `screenshots/manual/phase-<N>-<name>-summary.png` | **You** |

`demo-repo/` is never shared. `setup_phase.py` rebuilds it identically on every machine and re-applies earlier phases' work.

## Requirements on each machine
Windows, Python 3.9+, Node.js 20+, git, and Microsoft Edge (for report screenshots). No pip installs.

## Solo alternative
One person running everything in one session: use [`../00-MASTER-PROMPT.md`](../00-MASTER-PROMPT.md) instead.
