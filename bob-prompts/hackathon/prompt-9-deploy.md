# Prompt 9: Rebuild and redeploy the live dashboard on Vercel

**Run this in a Bob session on the laptop whose Vercel CLI is logged in** (`vercel whoami` prints a user). Any team member can drive it; name the summary screenshot after whoever does.

The live dashboard is already deployed at **https://bug-vaccine.vercel.app** (Vercel team `asherrs-projects`, project `bug-vaccine`), served from the static folder `site/`. This prompt rebuilds it from Bob's own results and redeploys it, so the live site always matches `bob-output/`.

---

You are running **Prompt 9** of the Bug Vaccine hackathon run, for team member **<YOUR NAME>**. **Bob feature showcased: Agent mode running a deployment end to end and verifying it.**

1. Read `bob-prompts/hackathon/_context.md` and follow it. N = 9. Do its "start of every prompt" step.
2. **Safety first.** Deployments are public. Never print, copy or commit any token. `vercel link` may create `site/.env.local` holding a `VERCEL_OIDC_TOKEN`; it must stay out of git (`site/.gitignore` has `.env*`) and out of the upload (`site/.vercelignore` has `.env*`). Check both files still contain `.env*` before deploying.
3. **Rebuild the site** from Bob's results:
   `python vaccine/dashboard.py --repo demo-repo --before bob-output/results-before.json --after bob-output/results-after.json --holdout bob-output/results-holdout.json --pr bob-output/results-pr.json --antibodies bob-output/antibodies.test.js --knowledge bob-output/knowledge.json --rag bob-output/rag-index.json --cure bob-output/cure.json --web-fonts --title "Bug Vaccine: IBM Bob run" --project "invoice-kit=bob-output/results-before.json,bob-output/results-after.json" -o site/index.html`
   (If `demo-repo/` is missing, run `python demo/build_demo_repo.py` first.)
4. **Deploy** from the `site/` folder:
   - `vercel whoami`. If it isn't logged in, stop and ask me to run `vercel login` myself. Never type credentials.
   - `cd site; vercel link --yes --project bug-vaccine --scope asherrs-projects; vercel deploy --prod --yes --scope asherrs-projects; cd ..`
   - Copy the deployment URL from the output into your log.
5. **Verify the live site**, using real HTTP responses, not assumptions:
   - `https://bug-vaccine.vercel.app/` must return 200. Check this with `curl.exe -s -o NUL -w "%{http_code}" <url>` or `Invoke-WebRequest`.
   - `https://bug-vaccine.vercel.app/.env.local` and `/.vercel/project.json` must return **404**. If either returns 200, stop immediately and tell me.
   - The page must contain `33%` and `invoice-kit`. Search the fetched HTML.
   - 📸 `-Name p9-live-site` with `https://bug-vaccine.vercel.app` open in a browser.
6. Make sure `README.md` has `**🌐 [Try the live dashboard](https://bug-vaccine.vercel.app)**` under the video link, and that `docs/challenge-alignment.md`'s "Submission checklist" has a row "Live demo | https://bug-vaccine.vercel.app | ✅ (verified: 200)". Add whichever is missing.
7. Write `bob-output/logs/prompt-9.md`: the commands, the deployment URL and every status code, copied from real output.
8. Finish with the end-of-prompt steps in `_context.md` (commit "Bob prompt 9: rebuild and redeploy the live dashboard"). Then tell me to save this session's summary as `bob_sessions/Prompt 9 summary - <YOUR NAME>.png` and push it.
