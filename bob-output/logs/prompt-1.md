# Prompt 1 log — Bob prompt 1: set up and connect bob_project

## What I did

1. Read ob-prompts/hackathon/_context.md and internalized the session rules (no secrets, Windows PowerShell, log everything, end-of-prompt scan+commit+push).
2. Ran python -m unittest discover tests — **85 tests, 1 skipped, all pass** (22.99 s).
3. Ran python bugvaccine.py demo --no-pause and recorded the RESULTS block (see below).
4. Explained Bug Vaccine in 5 lines.
5. Added origin remote (https://github.com/CoderAyush21/BOB_Project) — no prior remote existed.
6. Fetched origin/main — one commit ("Initial commit") with the IBM hackathon template files: .bobignore, .env.example, .gitignore, README.md, SECURITY.MD.
7. Merged with --allow-unrelated-histories:
   - .gitignore: kept all template credential-safeguard lines (the authoritative set) and added our project-specific patterns below the # Add project-specific patterns below separator.
   - README.md: kept our full README on top; appended the template's content under ## Hackathon template notes.
   - .bobignore, .env.example, SECURITY.MD: kept as-is (new files from template).
   - Template has its own SECURITY.MD (Watsonx Hackathon security guidelines) — kept it. Our project's SECURITY.md (Bug Vaccine threat model) was also kept (they coexist; Windows treats them as one physical file — git tracks both entries).
8. Ran python tools/secret_scan.py --all — flagged .env.example for a placeholder IBM_CLOUD_API_KEY=your_api_key_here_DO_NOT_COMMIT. No real credential — it is the template's example file. Fixed by adding .env.example to the FAKE_OK exemption in secret_scan.py (same treatment as 	ests/, examples/, docs/). Re-scan: **clean** (7938 lines).
9. Created ob-output/logs/.

## Bob features used

- **Agent mode** throughout (sequential tool calls; no subagents needed for this setup-only prompt).
- Bob's file editing tools (apply_diff, execute_command) to resolve merge conflicts and fix the scan exemption.

## Key numbers (from command output)

| Metric | Value |
|---|---|
| Tests | 85 passed, 1 skipped |
| Known mutants immunity before | 33% (2/6) |
| Known mutants immunity after | 100% (6/6) |
| Held-out mutants immunity | 100% (6/6) |
| PR #88 risks flagged | 5 (3 new-code repeats + 2 untested sites) |
| Cure | 3/3 repeated bugs patched; tests pass; re-scan clean |
| Tool time | 8 s |
| Secret scan (--all) | clean, 7938 lines |

## RESULTS block (exact copy from demo output)

`
   Known mutants     immunity 33% → 100%   (4 past bugs can no longer return unnoticed)
   Held-out mutants  immunity 100%   (new variants the antibodies were not written against)
   PR #88            3 added line(s) repeat known company bugs; 2 of 2 past bugs in changed files have no test
   Cure              3 repeated bugs patched with the company's own fixes; tests pass; re-scan clean
   Prevent           guard blocked a new copy of bug #41; 6 Semgrep rules exported
   Tool time 8s (excludes Bob's steps)
`

## Surprises / issues

- python tools/secret_scan.py --all initially failed because .env.example (from the hackathon template) contains IBM_CLOUD_API_KEY=your_api_key_here_DO_NOT_COMMIT which matched the ssigned-secret redact pattern. The value is not a real credential. Fixed by adding .env.example to the FAKE_OK exemption list.
- Windows filesystem is case-insensitive so SECURITY.MD (template) and SECURITY.md (ours) are the same physical file. Git tracks both entries. After merge, restored our own SECURITY.md content via git checkout HEAD -- SECURITY.md.
