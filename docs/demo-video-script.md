# Demo video script (target: 3 minutes)

> **Keep it to one story:** 33% → 100%, the blind check, the PR warning. The Debug lab, RAG and Company view are extras; show at most one of them, briefly, if time allows.

## 0:00–0:25 · The hook
**Screen:** the #57 postmortem, with the unticked follow-up highlighted.
**Say:** "This postmortem is from our sample project, but every team has one like it. The nightly invoice run crashed and 312 invoices didn't go out. The fix shipped. The follow-up, 'add a regression test', never happened. Every team has these. So: which of your old bugs can come back right now, without a single test failing?"

## 0:25–0:45 · The idea
**Screen:** the "How Bug Vaccine works" strip from the report.
**Say:** "Bug Vaccine turns your git history into a vaccine. IBM Bob reads your past fixes and incident reports, learns the pattern behind each bug, then hunts for every place it could come back, including code written *after* the fix."

## 0:45–1:30 · Bob at work (the Application of Technology part)
**Screen:** Bob live, sped up.
- Bob reading `antigens-raw.md` and the postmortem → **"document understanding"** (say it).
- Bob launching 3 subagents in parallel, one per bug pattern → **"parallel subagents"**.
- Show one subagent's finding: "reports.js repeats the float-money bug in `taxTotal()`."

## 1:30–2:00 · The uncomfortable number
**Screen:** `run.py` injecting bugs one by one, KILLED/SURVIVED scrolling, then the report at **33%**.
**Say:** "Four of six past bugs could come back today, and CI would stay green. And the new reports module repeats all three historical mistakes."

## 2:00–2:25 · Vaccinate
**Screen:** Bob in **Agent mode** writing the antibody tests, running them, and re-running the vaccine.
**Say:** "Bob writes tests that guard each bug *pattern*, not just the one mutant. No production code changes, only tests."
**Screen:** the gauge goes to **100%** with the before/after columns.

## 2:25–2:40 · "But isn't that circular?" (say it before the judges do)
**Screen:** a fresh Bob subagent generating held-out mutants, then `report-holdout.html`.
**Say:** "Bob wrote those tests while looking at the bugs, so we don't trust that 100%. A separate subagent that never saw the tests invents new variants of the same bugs. [State the real held-out score here, whatever it is.]"

## 2:40–2:52 · Where it lives: code review
**Screen:** the PR comment from `pr-comment.md`.
**Say:** "Run it on every pull request. This PR adds a loyalty feature that repeats three bugs we've already fixed, and a refunds module whose past-bug risks have no test. Bug Vaccine flags all five before merge."

## Optional, if you have 20 more seconds · It's also a debugger
**Screen:** dashboard → **Debug lab** → "JavaScript crash" example, then "Pull request diff".
**Say:** "Everything Bug Vaccine learns becomes company knowledge. Paste a crash, and it tells you we've had this bug before, which incident it was, and how we fixed it. Paste a pull request diff, and it flags the new lines that repeat old mistakes."

**Tip for recording:** turn on **Captions** and press **Play walkthrough**. The captions carry the narration for each step, with the real numbers from the run.

## 2:52–3:00 · Close
**Say:** "Every number here comes from actually running the tests, not an AI estimate. Bob proposes; the test runner decides. Bug Vaccine: your codebase never catches the same bug twice."

## Recording tips
- Record Bob sessions in full, then speed them up. Don't fake or stage them.
- Take the session-summary screenshots **straight after** each Bob task; they're required deliverables.
- Use 1080p and a large terminal font. Zoom the report to 125%.
