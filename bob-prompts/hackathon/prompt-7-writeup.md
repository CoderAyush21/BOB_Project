# Prompt 7: Verify, write up and publish

---

You are running **Prompt 7 of 7** of the Bug Vaccine hackathon run. **Bob feature showcased: multi-step orchestration and verification.**

1. Read `bob-prompts/hackathon/_context.md` and follow it. N = 7. Do its "start of every prompt" step.
2. **Re-verify every headline number yourself.** Don't trust the logs; re-run:
   - rebuild a clean patient: `python demo/build_demo_repo.py`
   - before: `python vaccine/run.py bob-output/mutants.json --repo demo-repo -o verify-before.json`
   - add the antibodies (`Copy-Item bob-output/antibodies.test.js demo-repo/test/`), then after: `python vaccine/run.py bob-output/mutants.json --repo demo-repo -o verify-after.json` and held-out: `python vaccine/run.py bob-output/mutants.holdout.json --repo demo-repo -o verify-holdout.json`
   Compare with `bob-output/results-before.json`, `results-after.json` and `results-holdout.json`. Report any mismatch; never hide one. Delete the `verify-*.json` files afterwards.
3. **Build the dashboard from your own results:**
   `python bugvaccine.py index demo-repo --source invoice-kit=bob-output/antigens.json -o bob-output/rag-index.json`, then
   `python vaccine/dashboard.py --repo demo-repo --before bob-output/results-before.json --after bob-output/results-after.json --holdout bob-output/results-holdout.json --pr bob-output/results-pr.json --antibodies bob-output/antibodies.test.js --knowledge bob-output/knowledge.json --rag bob-output/rag-index.json --cure bob-output/cure.json --web-fonts --title "Bug Vaccine: IBM Bob run" -o bob-output/dashboard.html`
   📸 `-Name p7-dashboard -Html bob-output/dashboard.html`
4. **Fill in `docs/how-bob-was-used.md`** from `bob-output/logs/`: replace every TODO with what actually happened in each prompt, the Bob features you **actually** used, real numbers only, and the screenshot file names in `screenshots/auto/` and `screenshots/manual/`. Keep the note that the tooling was drafted with another AI assistant (Claude), and state clearly which parts you (Bob) produced: everything in `bob-output/`, plus any code you changed.
5. **Compare with the reference answers.** You may now open `examples/` for the first time. Compare `bob-output/mutants.json` with `examples/mutants.example.json` and `bob-output/mutants.holdout.json` with `examples/mutants.holdout.json`. Add what you found that the reference missed (and the other way round) to `docs/how-bob-was-used.md` under "What Bob found that we didn't expect".
6. If your measured results differ from the numbers in `README.md` or `docs/problem-and-solution.md`, **show me the diff and wait for my OK** before saving; the submission should state Bob's real numbers.
7. Write `bob-output/README.md`: one paragraph saying these files were produced by IBM Bob during the hackathon run (with today's date), and a table of every file and what it is.
8. Check `screenshots/manual/`: list any prompt whose session-summary screenshot is missing.
9. Finish with the end-of-prompt steps in `_context.md` (commit "Bob prompt 7: verified results, dashboard and write-up"), then tell me:
   "Done. Remaining for you: save this session's summary screenshot as screenshots/manual/prompt-7-summary.png and push it (`git add screenshots/manual; git commit -m "screenshots: final session summary"; git push`), record the video (docs/demo-video-script.md), make the repo public, and submit."
