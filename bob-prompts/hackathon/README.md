# The IBM Bob hackathon run: 7 prompts (+2 follow-ups)

Paste them into IBM Bob **one at a time, in order** (Agent mode, with the `bug-vaccine` folder open). Each prompt ends by scanning for credentials, committing, and pushing to your `bob_project` GitHub repo.

| # | Prompt | Bob feature it showcases | Judging criterion it feeds |
|---|---|---|---|
| 1 | [Set up and connect `bob_project`](prompt-1-setup.md) | Agent mode | Presentation (public repo) |
| 2 | [Learn from history](prompt-2-antigens.md) | Document understanding | Application of Technology, Originality |
| 3 | [Hunt for re-entry points](prompt-3-hunt.md) | Parallel subagents | Application of Technology |
| 4 | [Re-infect and vaccinate](prompt-4-vaccinate.md) | Agent mode | Business Value (measured impact) |
| 5 | [Blind check](prompt-5-holdout.md) (**new session**) | Fresh subagent | Credibility of the numbers |
| 6 | [Code review, cure and prevent](prompt-6-pr-cure.md) | Subagents + Agent mode | Business Value, full solution |
| 7 | [Verify, write up and publish](prompt-7-writeup.md) | Orchestration and verification | Presentation |
| 8 | [Verify the post-run fix and check the deliverables](prompt-8-verify-fix.md) (**new session, any team member**) | Code review + independent verification | Credibility, complete submission |
| 9 | [Rebuild and redeploy the live dashboard](prompt-9-deploy.md) (Vercel CLI logged in) | Agent mode: deploy and verify | Presentation (live demo) |

**After each prompt:** screenshot Bob's task session summary (Win+Shift+S) and save it as `bob_sessions/prompt-N-summary.png`. The next prompt commits it. The hackathon requires these, from every team member.

**Pushing:** the first push may open a GitHub sign-in window (Git Credential Manager). Bob never force-pushes, and every push is preceded by `python tools/leak_scan.py`.
