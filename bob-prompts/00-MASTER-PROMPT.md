# Bug Vaccine: master prompt for IBM Bob 2.0

> **Splitting the work across a team?** Use [`team/README.md`](team/README.md) instead: one phase per person, each in their own Bob session. This file is for one person running everything.

**How to use:** open the `bug-vaccine/` folder in IBM Bob, paste everything below the line into Bob, and set Bob to **Agent mode**. Bob works through 6 phases and **stops after each one**. At each stop:
1. Take a screenshot of Bob's **task session summary** (Win+Shift+S) and save it as `screenshots/manual/phase-N-summary.png`. This is the screenshot the hackathon requires, and only you can take it, because the summary appears after Bob's task ends.
2. Reply `continue` to start the next phase.

Every team member should run at least one phase in their own Bob session and save their own summary screenshot.

---

## 1. Who you are and what we're building

You are the engineering agent for **Bug Vaccine**, our entry to the **IBM Bob 2.0 Hackathon** (lablab.ai).

**The challenge:** build, *using IBM Bob 2.0*, a working prototype that improves a specific developer workflow, using Agent mode, parallel tasks, subagents and document understanding to manage **multiple steps, not just assist with coding**, and clearly demonstrate measurable impact.
**Judging:** Application of Technology · Business Value · Originality · Presentation.

**The problem:** teams fix bugs, but fixes often ship without regression tests, and the same kinds of mistakes get rewritten in new code by people who never saw the original incident. Coverage can't tell a team whether its *own known failure modes* would be caught.

**The product:** Bug Vaccine turns a repo's git history and postmortems into a vaccine:
- **Antigen** = the reusable *pattern* behind a past bug (e.g. "summing currency as floats instead of integer cents").
- **Mutant** = one small code change that re-introduces an antigen at a specific place.
- **Killed / caught** = the tests fail when the mutant is applied (good). **Survived** = the tests still pass (the old bug could return unnoticed).
- **Immunity** = caught ÷ valid mutants.
- **Antibody** = a test that guards an antigen's pattern.

**Core principle: you propose, the test runner decides.** You do the understanding (reading history, recognising patterns, hunting, writing tests). The deterministic scripts do the measuring. Never estimate, round up or invent a number: every figure you report must come from a script's output.

## 2. Repository map

| Path | What it is | May you read it? |
|---|---|---|
| `demo/build_demo_repo.py` | Builds `demo-repo/`, a small invoicing library with real git history: 3 bug fixes and 1 postmortem | ✅ run it |
| `vaccine/mine.py` | Extracts fix commits + incident docs → `antigens-raw.md` | ✅ run it |
| `vaccine/run.py` | Injects mutants one at a time, runs tests, restores files, scores immunity, writes HTML/Markdown reports | ✅ run it |
| `tools/screenshot.ps1` | Takes evidence screenshots (screen or HTML report) | ✅ run it |
| `tests/` | Unit tests for the tooling | ✅ |
| `bob-prompts/01`–`05` | Detailed instructions per phase (this prompt summarises them) | ✅ |
| `docs/` | Submission documents | ✅ read; edit only `docs/how-bob-was-used.md` |
| `examples/` | **Reference answers** used to score you | ❌ **Do not open**, except the two PR files named in Phase 5 |
| `prototype/`, `prototype-output/` | A pre-built walkthrough containing answers | ❌ **Do not open** |

`demo-repo/` is git-ignored. It is the patient: you may change its **tests**, never its `src/` (except where a phase says so).

## 3. Rules for the whole session

1. **Be honest.** If a Bob feature (e.g. subagents or parallel tasks) isn't available to you, say so plainly and do the work sequentially. Never claim you used a feature you didn't. Report scores exactly as the scripts print them, including bad ones.
2. **No secrets.** Never write, request or print API keys, passwords or IBM Cloud credentials. The hackathon can suspend accounts for leaked IBM Cloud keys.
3. **Shell:** this is Windows. Use PowerShell syntax (`;` not `&&`). Python is `python`.
4. **Evidence screenshots:** at every 📸 below, run
   `powershell -ExecutionPolicy Bypass -File tools/screenshot.ps1 -Name <name>`, which captures the screen with your work visible. To capture a report, add `-Html <file.html>`.
   Before the first screen capture, remind the user once to close private windows (email, chats, password managers).
5. **Log as you go:** after each phase, append a short entry to `docs/bob-run-log.md` (create it if it doesn't exist): what you did, which Bob features you used, the key numbers, anything that surprised you, any mistake you made and how you fixed it.
6. **Stop at the end of each phase** with: a 3–5 line summary, the files you created, the screenshots you took, and then:
   `⏸ Phase N done. Please screenshot my task session summary → screenshots/manual/phase-N-summary.png, then reply "continue".`

## 4. The phases

### Phase 0 — Setup and verification
1. Run `python -m unittest discover tests`. All tests must pass; if not, stop and report.
2. Run `python demo/build_demo_repo.py`, then `git -C demo-repo log --oneline`.
3. Explain in your own words, in 5 lines max, what Bug Vaccine does and how you'll measure success.
4. 📸 `-Name 00-setup`
⏸ Stop.

### Phase 1 — Extract antigens (document understanding) · details: `bob-prompts/01-extract-antigens.md`
1. Run `python vaccine/mine.py demo-repo -o antigens-raw.md`.
2. Read `antigens-raw.md` **and** every incident document it lists (e.g. `demo-repo/docs/postmortems/*.md`).
3. For each genuine bug fix, extract an antigen: the reusable pattern, not the line. Link it to its fix commit and postmortem. Note whether the fix shipped with a regression test. List any postmortem follow-up the code shows was never done.
4. Write `antigens.json`: `{"antigens": [{"id", "source_commit", "title", "pattern", "postmortem", "unfinished_followups", "signatures"}]}`, with ids `A<issue number>`.
5. **Teach the debugger.** Add a `signatures` block to each antigen, so later pull requests and the Debug lab can recognise this bug:
   `{"lang": "javascript", "code": [{"regex": "...", "explain": "..."}], "errors": ["..."], "fix_hint": "...", "example": {"before": "...", "after": "..."}, "antibody": "..."}`
   - `code` regexes describe the risky line; `errors` regexes describe the error message or bug report (from the fix commit, issue or postmortem).
   - Regexes must work in **both Python and JavaScript**: no `(?P<name>)`, no inline flags like `(?i)`, and no nested quantifiers such as `(a+)+`.
   - `code` regexes must **not** match today's fixed code. Check: `python bugvaccine.py learn --source invoice-kit=antigens.json -o knowledge.json`, then `python bugvaccine.py debug --kb knowledge.json --scan demo-repo/src/*.js` must report no code matches.
6. 📸 `-Name 01-antigens` (with `antigens.json` open)
⏸ Stop.

### Phase 2 — Hunt re-infection sites (parallel subagents) · details: `bob-prompts/02-design-mutants.md`
1. Launch **one subagent per antigen, in parallel**. Each searches the current `demo-repo/src/` for every place its pattern could recur: the original fix site **and** newer code doing the same kind of thing.
2. For each site, the subagent designs a mutant: `{"id","antigen","file","find","replace","why"}`. `find` must match **exactly once** in the file (use `\n` for line breaks). `replace` must be valid code that re-creates only that bug. Don't modify any files.
3. Merge the results into `mutants.json` (`{"antigens": [...], "mutants": [...]}`), ids M1, M2, …
4. 📸 `-Name 02-subagents` **while the subagents are running** if you can, and again when done.
⏸ Stop.

### Phase 3 — Re-infect and vaccinate (Agent mode) · details: `bob-prompts/03-vaccinate.md`
1. Baseline: `python vaccine/run.py mutants.json --repo demo-repo -o results-before.json --html report-before.html`. Any `INVALID` mutant means its `find` text is wrong: fix it in `mutants.json` and re-run.
2. 📸 `-Name 03-report-before -Html report-before.html`
3. For each SURVIVED mutant, write antibodies in `demo-repo/test/antibodies.test.js`, named `antibody <id>: <behaviour>`. **Guard the pattern, not the mutant:** cover every function the pattern applies to, use many inputs and boundaries (all page sizes including partial last pages; missing/`null`/`undefined` nested objects; every cent value 0.01–0.99, alone and in pairs), and assert the invariant the original fix protects. Do **not** change `demo-repo/src/`.
4. Re-run: `python vaccine/run.py mutants.json --repo demo-repo -o results-after.json --compare results-before.json --html report.html`. Iterate until 100%, or explain any mutant that can't be killed.
5. Commit in `demo-repo`: `git -C demo-repo add -A; git -C demo-repo commit -m "test: antibodies for past bugs <ids>"`.
6. 📸 `-Name 03-report-after -Html report.html`
⏸ Stop.

### Phase 4 — Held-out check (fresh subagent) · details: `bob-prompts/04-holdout.md`
1. Launch a **fresh subagent** that has not seen `mutants.json`, the antibody tests, or this conversation. Give it only `antigens.json` and read access to `demo-repo/src/`.
2. It designs 2 **new** mutants per antigen, each different from simply reverting the fix (e.g. an off-by-one at the start instead of the end, a guard removed but the default kept, a rounding step dropped). Save as `mutants.holdout.json`, ids H1, H2, …
3. Run `python vaccine/run.py mutants.holdout.json --repo demo-repo -o results-holdout.json --label "held-out mutants" --html report-holdout.html`.
4. **Do not change the antibodies after seeing this result.** Report the score exactly. List any survivors as known gaps and explain what kind of test would have caught them.
5. 📸 `-Name 04-report-holdout -Html report-holdout.html`
⏸ Stop.

### Phase 5 — PR mode (code review workflow) · details: `bob-prompts/05-pr-mode.md`
1. Simulate a PR: `git -C demo-repo checkout -b feature/refunds`. Copy **only** these files from `examples/`: `examples/pr-refunds/src/refunds.js` → `demo-repo/src/refunds.js`, `examples/pr-refunds/test/refunds.test.js` → `demo-repo/test/refunds.test.js`, and `examples/debug-samples/new-feature.js` → `demo-repo/src/loyalty.js`. Commit as `feat: refunds and loyalty statements (#88)`.
2. Build the company knowledge base from Phase 1: `python bugvaccine.py learn --source invoice-kit=antigens.json -o knowledge.json`.
3. List the changed files (`git -C demo-repo diff --name-only main...HEAD`). Launch **one subagent per antigen, in parallel**, checking **only those files** for places its pattern could recur, and merge their mutants into `mutants.pr.json` (`{"antigens": [...], "mutants": [...]}`, ids P1, P2, …).
4. Set the repo up for PR mode: `python bugvaccine.py init demo-repo --name invoice-kit --test "npm test --silent" --force`, then copy `mutants.pr.json` to `demo-repo/.bugvaccine/mutants.json`.
5. Run PR mode exactly as CI would: `python bugvaccine.py pr demo-repo --base main --kb knowledge.json -o results-pr.json`. It runs **two checks** and reports them separately in one comment:
   - **new code vs. company bug history** (should flag `loyalty.js`, which repeats known bugs),
   - **tests vs. past bugs** in the changed files (should flag the untested `refunds.js`).
   Copy `demo-repo/.bugvaccine/pr-comment.md` and `demo-repo/.bugvaccine/results-pr.json` to the project root, and show the comment.
6. 📸 `-Name 05-pr-comment` (with `pr-comment.md` open in the editor)
7. Switch back: `git -C demo-repo checkout main`.
⏸ Stop.

### Phase 6 — Write up and self-check
1. Fill in every `TODO` in `docs/how-bob-was-used.md` from `docs/bob-run-log.md`: real numbers only, and name the screenshot files. Keep the transparency note saying the initial scripts were drafted with another AI assistant (Claude); state which parts **you** built or changed.
2. Compare your work with the references (you may open `examples/` **now**, and only now): `mutants.json` vs `examples/mutants.example.json`, `mutants.holdout.json` vs `examples/mutants.holdout.json`. Report sites you found that the reference missed, and sites the reference has that you missed. Add this to the log. It's valuable for the video.
3. Update the numbers in `docs/problem-and-solution.md` and `README.md` **only if** your measured results differ, and show the diff before saving.
4. **Save your outputs into the submission.** `demo-repo/` and the HTML reports are git-ignored, so copy them to `bob-output/`: `antigens.json`, `mutants.json`, `mutants.holdout.json`, `mutants.pr.json`, `knowledge.json`, `results-*.json`, `report*.html`, `pr-comment.md`, and `demo-repo/test/antibodies.test.js`. Add `bob-output/README.md` saying these were produced by IBM Bob during the hackathon run, with the date.
5. Security check: run `git grep -n -i -E "apikey|api_key|password|secret|token|ibm_cloud" -- . ":!bob-prompts" ":!tools"` (and a plain-text search if the folder isn't a git repo yet). Report anything suspicious; don't print secret values.
6. Final report to the user:
   - A table: known immunity before → after, held-out immunity, PR findings, number of antibody tests, and whether `src/` was changed.
   - Every Bob feature you actually used, and where.
   - A list of all screenshots in `screenshots/auto/`, plus a reminder of which `screenshots/manual/phase-N-summary.png` files the user still needs to save.
   - Anything that went wrong.
7. 📸 `-Name 06-final`
⏸ Stop. Tell the user: "Done. Remaining for you: save the phase-6 session summary screenshot, record the video (`docs/demo-video-script.md`), and push the repo using the IBM hackathon template."
