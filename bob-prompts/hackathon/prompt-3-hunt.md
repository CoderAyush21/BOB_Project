# Prompt 3: Hunt for re-entry points (parallel subagents)

---

You are running **Prompt 3 of 7** of the Bug Vaccine hackathon run. **Bob features showcased: subagents and parallel tasks.**

1. Read `bob-prompts/hackathon/_context.md` and follow it. N = 3. Do its "start of every prompt" step.
2. If `demo-repo/` is missing, rebuild it with `python demo/build_demo_repo.py`. Read `bob-output/antigens.json`.
3. **Launch one subagent per antigen, in parallel.** Each searches the current `demo-repo/src/` for **every** place its pattern could come back: the original fix site **and** any other code, especially code written after the fix, that does the same kind of thing. For each place it designs one mutant:
   `{"id", "antigen", "file", "find", "replace", "why"}`: `find` is an exact substring that occurs **exactly once** in that file (`\n` for line breaks); `replace` is valid code that re-creates only that bug; `why` links it to the historical bug. Don't modify any files.
4. 📸 `-Name p3-subagents` **while the subagents are running**, if you can.
5. Merge the results into `bob-output/mutants.json`: `{"antigens": <copied from antigens.json>, "mutants": [...]}`, ids M1, M2, …
6. Validate without running tests: every `find` must match exactly once in its file (a short Python check is fine). Fix any that don't.
7. In your log, list how many subagents ran, what each found, and which sites are in code written **after** the original fix.
8. 📸 `-Name p3-mutants` with `bob-output/mutants.json` open.
9. Finish with the end-of-prompt steps in `_context.md` (commit "Bob prompt 3: parallel hunt for re-entry points").
