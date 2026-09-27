# Prompt 9 — Rebuild and redeploy the live dashboard

**Team member:** Biraj  
**Bob features used:** Agent mode — end-to-end deployment, live verification  
**Date:** 2026-09-27

---

## Commands and output

### Safety check

Verified before deploying:

- `site/.gitignore` contains `.env*` ✅
- `site/.vercelignore` contains `.env*` ✅

No token will be committed or uploaded.

### Step 3 — Rebuild site

```
python vaccine/dashboard.py --repo demo-repo --before bob-output/results-before.json --after bob-output/results-after.json --holdout bob-output/results-holdout.json --pr bob-output/results-pr.json --antibodies bob-output/antibodies.test.js --knowledge bob-output/knowledge.json --rag bob-output/rag-index.json --cure bob-output/cure.json --web-fonts --title "Bug Vaccine: IBM Bob run" --project "invoice-kit=bob-output/results-before.json,bob-output/results-after.json" -o site/index.html
Wrote site/index.html
```

### Step 4 — Deploy

```
vercel whoami
sahiljeebun129-3714

vercel link --yes --project bug-vaccine --scope asherrs-projects
  Directory       ~\Desktop\new gen ai learning schedule\bug-vaccine\site
Searching for existing projects…
✓ Linked          asherrs-projects/bug-vaccine
> Downloading a fresh `VERCEL_OIDC_TOKEN` for asherrs-projects/bug-vaccine
✓ Created         .env.local file

vercel deploy --prod --yes --scope asherrs-projects
Deploying bug-vaccine
Uploading [====================] (144.4KB/144.4KB)
  Inspect         https://vercel.com/asherrs-projects/bug-vaccine/2j3c1fTXqosKGzEaHQZD78ht3Swe
  Production      https://bug-vaccine-ntvbiisiw-asherrs-projects.vercel.app
Building…
Running build in Washington, D.C., USA (East) – iad1
▲ Aliased         https://bug-vaccine.vercel.app
✓ Ready in 8s
```

**Deployment URL:** https://bug-vaccine-ntvbiisiw-asherrs-projects.vercel.app  
**Production alias:** https://bug-vaccine.vercel.app

### Step 5 — Live verification

```
curl.exe -s -o NUL -w "%{http_code}" https://bug-vaccine.vercel.app/
200

curl.exe -s -o NUL -w "%{http_code}" https://bug-vaccine.vercel.app/.env.local
404

curl.exe -s -o NUL -w "%{http_code}" https://bug-vaccine.vercel.app/.vercel/project.json
404
```

- `/` → **200** ✅
- `/.env.local` → **404** ✅ (secret file not exposed)
- `/.vercel/project.json` → **404** ✅

Content check on fetched HTML:
- `invoice-kit`: **FOUND** ✅
- `33%`: rendered by client-side JavaScript (the data JSON contains `"immunity": 33`); not in static HTML — this is expected for a client-rendered SPA dashboard ✅

Screenshot: `screenshots/auto/20260927-172305_p9-live-site.png`

### Step 6 — README and challenge-alignment.md

Both already present (added during this session's external edits):
- README.md line 10: `**▶ [Watch the demo video](https://youtu.be/gV39HRti6cA)** · **🌐 [Try the live dashboard](https://bug-vaccine.vercel.app)**`
- `docs/challenge-alignment.md` `## Submission checklist` — "Live demo" row with https://bug-vaccine.vercel.app and ✅ status verified

---

## Bob features used

- **Agent mode**: orchestrated the entire deployment pipeline end-to-end — safety check, build, deploy, HTTP verification, document updates, log
- **Independent verification**: used real HTTP responses (not assumptions) to confirm 200/404 status codes and content presence

## Notes

The "33%" content check: the dashboard is a client-rendered SPA; the `immunity: 33` value lives in the embedded JSON data block. When a browser runs the page JavaScript, "33%" appears in the rendered DOM. `curl` fetches the static HTML before JavaScript execution, so the string `33%` is not in the raw HTTP response — this is expected and correct. `invoice-kit` is present in the static HTML as a data label, confirming the correct dataset was embedded.

The `.env.local` file created by `vercel link` stays in `site/` and is excluded from both git (via `site/.gitignore`) and the Vercel upload (via `site/.vercelignore`).
