# Prompt 1: Set up and connect the `bob_project` repository

**Before pasting:** replace `REPO_URL` below with your GitHub repo's URL (e.g. `https://github.com/<your-username>/bob_project.git`). Open the `bug-vaccine` folder in IBM Bob, in **Agent mode**.

---

You are running **Prompt 1 of 7** of the Bug Vaccine hackathon run. REPO_URL = `REPO_URL`

1. Read `bob-prompts/hackathon/_context.md` and follow it for this whole session. N = 1.
2. **Verify the project.** Run `python -m unittest discover tests`. All tests must pass; if not, stop and tell me. Then run `python bugvaccine.py demo --no-pause` and report its RESULTS block exactly as printed.
3. **Explain** in 5 lines max, in your own words, what Bug Vaccine does, which developer workflow it improves, and how you'll measure success.
4. **Connect the repository** (never force-push, never delete history):
   - `git remote -v`. If there's no `origin`, run `git remote add origin REPO_URL`; if `origin` points elsewhere, ask me before changing it.
   - `git fetch origin`. If `origin/main` exists and has commits (for example files from the IBM hackathon template), merge it: `git merge origin/main --allow-unrelated-histories -m "Merge the hackathon template"`. Resolve conflicts like this:
     - `.gitignore`: keep **every** line from both sides (the template's lines are credential safeguards).
     - `README.md`: keep ours on top, and keep any template section about submission requirements below it under a heading "Hackathon template notes".
     - Keep every other template file. If the template has its own LICENSE, keep it and tell me.
   - Show me the final `git status` and file list.
5. **Credential check of everything:** `python tools/leak_scan.py --all` must print `clean`. If it doesn't, stop.
6. `mkdir bob-output/logs` (if missing). 📸 `-Name p1-setup` (with the terminal showing the test results and the demo RESULTS).
7. Finish with the end-of-prompt steps in `_context.md` (scan, commit "Bob prompt 1: set up and connect bob_project", push with `git push -u origin main`).
