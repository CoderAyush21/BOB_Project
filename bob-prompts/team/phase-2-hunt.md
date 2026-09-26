# Phase 2: Hunt re-infection sites (parallel subagents)

**Before you start:** `git pull`. Replace `<MEMBER>` below with your first name. Then paste everything below the line into IBM Bob (Agent mode).
**Needs:** Phase 1 (`bob-output/antigens.json`). **Unlocks:** Phase 3.

---

My name is **<MEMBER>**. You are running **Phase 2: Hunt re-infection sites** of Bug Vaccine.

1. Read `bob-prompts/team/_shared-context.md` and follow its rules for this whole session. PHASE = 2, MEMBER = <MEMBER>.
2. Setup: `python tools/setup_phase.py 2`. If it fails, stop and tell me what's missing.
3. Read `bob-output/antigens.json`.
4. Launch **one subagent per antigen, in parallel**. Each subagent searches the current `demo-repo/src/` for **every** place its pattern could recur: the original fix site **and** any other code, especially code written after the fix, that does the same kind of thing.
5. For each site, the subagent designs one mutant: `{"id","antigen","file","find","replace","why"}`.
   - `find`: an exact substring that occurs **exactly once** in that file (`\n` for line breaks).
   - `replace`: valid, runnable code that re-creates only that bug.
   - `why`: the link to the historical bug.
   - Don't modify any files.
6. 📸 `-Name p2-<MEMBER>-subagents` **while the subagents are running**, if possible.
7. Merge everything into `bob-output/mutants.json`: `{"antigens": <copied from antigens.json>, "mutants": [...]}`, ids M1, M2, …
8. Validate it without running tests: for every mutant, confirm `find` occurs exactly once in its file (a quick Python check is fine). Fix any that don't.
9. 📸 `-Name p2-<MEMBER>-mutants` with `bob-output/mutants.json` open.
10. Write your log (include how many subagents ran and what each found), commit, and finish as the shared rules describe.
