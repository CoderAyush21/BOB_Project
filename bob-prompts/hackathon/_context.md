# Bug Vaccine: context for every hackathon prompt (IBM Bob: read this first)

## The challenge you are part of
**IBM Bob 2.0 Hackathon (lablab.ai).** Build, *using IBM Bob 2.0*, a working prototype that improves a specific developer workflow (here: **testing, debugging, code review and application maintenance**), using **Agent mode, parallel tasks, subagents and document understanding** to manage multiple steps, not just assist with coding, and clearly demonstrate impact: less manual effort, fewer errors and less rework.
Judging: **Application of Technology · Business Value · Originality · Presentation.**
Required deliverables include IBM Bob task session summary screenshots and exported session reports (in `bob_sessions/`, which the template requires) and a public repository. **IBM Cloud credentials must never be committed.**

## The product
Bug Vaccine turns a repo's own bug history into protection:
- **Antigen**: the reusable *pattern* behind a past bug, plus `signatures` (what the buggy code and error look like) and `patches` (a fix recipe from the original fix).
- **Mutant**: one small change that re-introduces an antigen at one place. **Caught**: the tests fail with it. **Survived**: the bug could return unnoticed. **Immunity** = caught ÷ valid mutants.
- **Antibody**: a test that guards an antigen's pattern.
- **Cure and prevent**: `patch` applies the team's past fixes, `guard` blocks commits that repeat known bugs, `rules` exports lint rules.

**Core principle: you propose, the test runner decides.** Never estimate, round or invent a number; every figure must come from a command's output. If a Bob feature (subagents, parallel tasks) isn't available to you, say so and work sequentially. Never claim a feature you didn't use.

## Files
| Path | Access |
|---|---|
| `bugvaccine.py`, `vaccine/`, `tools/`, `demo/` | run them |
| `demo-repo/` | the patient (git-ignored, built by `python demo/build_demo_repo.py`). Change its **tests**, never its `src/` unless a prompt says so. |
| `bob-output/` | **everything you produce goes here** (committed; the judges see it) |
| `bob-output/logs/prompt-N.md` | your log for prompt N |
| `examples/`, `prototype/`, `prototype-output/` | **reference answers: never open**, except the files a prompt names explicitly |

## Rules for every prompt
1. **Windows / PowerShell:** use `;` not `&&`. Python is `python`.
2. **Screenshots you take:** at each 📸 run `powershell -ExecutionPolicy Bypass -File tools/screenshot.ps1 -Name pN-<what>` (add `-Html <file.html>` to capture a report). Before your first screen capture in a session, ask me to close private windows and wait for my OK.
3. **No secrets:** never write, request or print API keys, passwords or IBM Cloud credentials.
4. **Log:** write `bob-output/logs/prompt-N.md`: what you did, which Bob features you actually used and how, the key numbers (copied from command output), anything surprising, and any mistake you made and fixed.

## Start of every prompt (except prompt 1)
If I saved last prompt's session-summary screenshot, commit it first:
`git add bob_sessions; git commit -m "bob_sessions: session summary for the previous prompt"` (skip if there's nothing to commit).

## End of every prompt: scan, commit, push
1. `git add -A`
2. `python tools/leak_scan.py`. It **must** print `clean`. If it doesn't, **stop**, don't commit, and tell me which file and rule it reported (never print the value).
3. `git commit -m "Bob prompt N: <one-line summary>"`
4. `git push origin main`. If the push is rejected, **never force-push**: run `git pull --no-rebase origin main`, resolve any conflict (keep both sides' content), run the scan again, and push. If it still fails, stop and show me the error.
5. Finish with a 3–5 line summary, then tell me:
   `✅ Prompt N done and pushed. Please screenshot my task session summary → bob_sessions/prompt-N-summary.png (and export the session report there if Bob offers it), then paste prompt N+1.`
