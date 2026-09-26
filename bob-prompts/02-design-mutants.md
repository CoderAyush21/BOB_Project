# Prompt 2 — Hunt for re-infection sites (Bob, Agent mode, parallel subagents)

> Screenshot the session summary → `screenshots/`.

---

Read `antigens.json`. Launch **one subagent per antigen, in parallel**.

Each subagent searches the **current** code in `demo-repo/src/` for every place where its bug pattern could occur. That means the original fix site *and* any newer code that does the same kind of thing. For each site, it designs a **mutant**: the smallest text change that reintroduces that exact bug there.

Rules for mutants:
- `find` must be an exact substring that appears **exactly once** in the file. Use `\n` for multi-line.
- `replace` must be valid code that runs; it re-creates the bug and nothing else.
- Add a `why` explaining the link to the historical bug.
- Do not modify any files. Only describe mutants.

Merge all subagent output into `mutants.json` with this format: `{"antigens": [...], "mutants": [{"id","antigen","file","find","replace","why"}]}`.
Do NOT read anything in `examples/` or `prototype/`. Those hold reference answers used to score you afterwards.
