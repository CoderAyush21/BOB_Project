# Using Bug Vaccine on your own repository

Bug Vaccine answers one question: **"If a bug we've already fixed came back, would our tests notice?"** Then it helps you fix the places where they wouldn't.

## Is it a good fit?

| Good fit | Poor fit |
|---|---|
| A few months or more of git history with real `fix` commits | A brand-new repo with no bug history |
| A test suite that runs in seconds to a few minutes | A suite that takes 30+ minutes (each mutant = one test run; see "Cost") |
| Bugs that recur: validation, boundaries, null handling, money, error types, parsing | Bugs that only show up in integration environments your tests can't reach |
| You want a *targeted* check linked to real incidents | You want exhaustive mutation testing (use Stryker, PIT or mutmut) |

## Setup (5 minutes)

Requirements: Python 3.9+, git, and whatever your own tests need. No pip installs.

Get the tool (clone your team's copy of this repository, or download it as a ZIP and unpack it) next to your repos, then:

```bash
python bug-vaccine/bugvaccine.py init path/to/your-repo --test "<your test command>" --name billing-api
```

`init` creates `your-repo/.bugvaccine/` (config, a Bob prompt, a `.gitignore`) and **checks that your test command passes** on the unmodified code before anything else happens. If it fails, it shows the last lines of output and a hint. It also tells you roughly how long a vaccine run will take.

- `--name` is the project's name across the company (knowledge base, RAG, dashboard). It defaults to the folder name; set it when folder names aren't unique (two repos both called `api`).
- The generated `PROMPT.md` refers to the tool by a **relative** path, so it works for teammates who keep `bug-vaccine` in the same place relative to the repo. Commit it.

All commands below are written as `python bugvaccine.py ...`; from another folder, use the path to it, e.g. `python bug-vaccine/bugvaccine.py ...`.

### Test command examples

| Stack | `--test` |
|---|---|
| Node (npm) | `"npm test --silent"` |
| Python (pytest) | `"pytest -q -x"` |
| Python (unittest, `src/` layout), Windows | `"set PYTHONPATH=src&& python -m unittest -q"` |
| Python (unittest, `src/` layout), macOS/Linux | `"PYTHONPATH=src python -m unittest -q"` |
| Go | `"go test ./..."` |
| Java (Maven) | `"mvn -q test"` |
| Rust | `"cargo test --quiet"` |

Tip: call the test runner directly rather than through a package manager (`node --test` instead of `npm test`: npm's own start-up adds about 1.5 s to *every* mutant run), and point `--test` at the **fastest subset** that covers the code you're vaccinating (e.g. `pytest -q tests/unit`). The exit code is all that matters: 0 = tests pass.

## The workflow

| Step | Command / who | Output in `.bugvaccine/` |
|---|---|---|
| 1. Mine history | `python bugvaccine.py mine <repo>` | `antigens-raw.md` |
| 2. Extract antigens | **Bob**: `PROMPT.md` Phase 1 | `antigens.json` |
| 3. Hunt | **Bob**: `PROMPT.md` Phase 2 | `mutants.json` |
| 4. Validate | `python bugvaccine.py check <repo>` | (checks each `find` matches once) |
| 5. Measure | `python bugvaccine.py run <repo> --html -o results-before.json` | `results-before.json`, `report.html` |
| 6. Vaccinate | **Bob**: `PROMPT.md` Phase 3 (writes tests in your repo), then `python bugvaccine.py run <repo> --html -o results-after.json --compare results-before.json` | your test files, `results-after.json` |
| 7. Held-out check | **Bob**: `PROMPT.md` Phase 4, in a fresh session | `results-holdout.json` |
| 8. Keep it working | CI: [`integrations/github-actions/bug-vaccine.yml`](../integrations/github-actions/bug-vaccine.yml) | PR comment + gate |

Commit `config.json`, `PROMPT.md`, `antigens.json` and `mutants.json`. Results, reports and dashboards are git-ignored.

Always name the "before" run: a plain `run` writes `results.json`, and a second plain run would overwrite it and lose your comparison.

Steps 2, 3, 6 and 7 need an AI agent. The prompt is written for IBM Bob, but it's plain instructions and works with other coding agents too.

## In CI

Set a gate in `.bugvaccine/config.json`, e.g. `"min_immunity": 90`, and add the GitHub Actions workflow. `bugvaccine.py pr` runs **two checks** and reports them separately in one PR comment:

1. **New code vs. company bug history.** Every line the PR adds is compared with known bug signatures (from `.bugvaccine/company-knowledge.json`, or `--kb`, or else this repo's own patterns). This catches brand-new files that repeat old mistakes.
2. **Tests vs. past bugs.** Stored mutants in the files the PR changed are re-injected, to check the tests still catch them.

The comment only shows ✅ when something was actually checked and nothing was found; if nothing could be checked, it says so. The job fails if immunity drops below the gate or a mutant is **stale** (the code it targets was rewritten, so re-run the Bob hunt). Add `--fail-on-new-risks` to also fail when added lines repeat known bugs.

**Limitation:** signatures recognise known *shapes* of past bugs. A new variation that looks different is found by the **Bob hunt on the PR** (`bob-prompts/05-pr-mode.md`).

## Debugging with company knowledge (the Debug lab)

Every repo you vaccinate also teaches the **debugger**. In Phase 1, Bob gives each bug pattern a `signatures` block (what the risky code and the error look like, and how it was fixed). Merge them across the company:

```bash
python bugvaccine.py learn repo-a repo-b repo-c -o company-knowledge.json          # "training"
python bugvaccine.py learn repo-d -o company-knowledge.json --merge                # add a repo later
```

Then debug against it, from the command line or in the dashboard's **Debug lab** tab:

```bash
python bugvaccine.py debug --kb company-knowledge.json --error "TypeError: Cannot read properties of undefined (reading 'email')"
python bugvaccine.py debug --kb company-knowledge.json --scan src/new_feature.js      # review new code
python bugvaccine.py debug --kb company-knowledge.json --error-file crash.log --prompt # + a Bob prompt
git diff main | python bugvaccine.py debug --kb company-knowledge.json --diff -       # review only a PR's new lines
python bugvaccine.py dashboard your-repo --kb company-knowledge.json                  # Debug lab in the UI
```

For each match you get the known bug, the matching line or error text, how it was fixed before, a before/after example, the test to add, and the past incident. In the Debug lab you can also **teach it a new bug** from the page: it tests your rule live against what you pasted, keeps it in your browser, and copies it as JSON for the team's knowledge base.

### Ask your company's history (RAG)

Retrieval-augmented generation grounds the assistant in your own bug history instead of its general knowledge:

```bash
python bugvaccine.py index repo-a repo-b --docs runbooks/*.md -o rag-index.json          # build the corpus
python bugvaccine.py ask "nightly job crashed: Cannot read properties of undefined" \
       --index rag-index.json --kb company-knowledge.json --prompt                        # retrieve + prompt
python bugvaccine.py dashboard your-repo --kb company-knowledge.json --rag rag-index.json  # sources in the Debug lab
```

- **Indexed:** fix commits (message and changed lines), postmortem sections, learned bug patterns, and any docs you add.
- **Retrieval:** hybrid. BM25 keyword ranking with code-aware tokens, plus a boost for bug patterns whose signatures match. That's why `0.30000000000000004` finds the float-money bug even though they share no words.
- **Generation:** the prompt gives Bob numbered sources and requires citations like `[2]`, and tells it to say "Our history doesn't cover this" rather than guess.
- **Privacy:** everything runs locally, no embeddings API is called, and every chunk is secret-redacted at index time.

**What "training" means here:** there is no machine-learning model. It's a curated set of your company's own bug patterns, written by Bob from real history and checked by tests. So its answers are explainable (it always shows *why* it matched), and it only recognises bugs you've had before. For anything new it says so plainly and gives you a Bob prompt that includes what the company already knows.

## Troubleshooting

| Problem | Fix |
|---|---|
| `init` says the tests fail, and the output mentions `FileNotFoundError` or "Filename too long" (Windows) | Windows limits paths to 260 characters. Move the repo to a shorter path (e.g. `C:\src\repo`), or enable long paths: `git config --global core.longpaths true` **and** the Windows *LongPathsEnabled* setting (admin), then re-clone. |
| `git clone` says "Filename too long" | Same as above. |
| A mutant shows `INVALID ... matches 0 times` | The code moved on since the mutant was written. Re-run the Bob hunt (Phase 2) for that file. |
| `learn` says two repos have the same name | Use `name=path`, e.g. `learn billing=repos/api payments=../other/api`, or set `"name"` in each `config.json`. |
| `pr` says `REFUSED` | The PR edits `.bugvaccine/config.json`. A maintainer should review it, then re-run with `--allow-config-change` (or pass `--test` explicitly, as CI does). |

## Cost

Each mutant costs one full run of your test command. With a 2-second suite, 20 mutants take about 40 seconds; with a 5-minute suite, 20 mutants take over an hour. Use a faster `--test` subset, fewer and higher-value mutants, and PR mode, which only runs mutants in changed files.

## Limitations (read before relying on it)

- **Mutants are exact text replacements** in one file. If the code is reformatted or refactored, a mutant goes *stale* (reported as invalid; the CI gate fails so you notice). Refresh with the Bob hunt.
- **It modifies your working tree temporarily.** Every mutated file is restored after each run (including on Ctrl+C), but commit or stash first. `run` warns you if the files it will touch have uncommitted changes.
- **It runs your test command through the shell.** Only use commands you trust.
- **"Survived" doesn't always mean "bug".** Some mutants are *equivalent*: harmless changes like an error message's wording. Phase 3 asks Bob to label these instead of writing pointless tests.
- **Immunity is only as good as the mutants.** A high score means your tests catch *these* re-injected bugs, not every possible bug. The held-out check (Phase 4) tells you whether the tests generalise.
- **Python caches are handled** (`PYTHONDONTWRITEBYTECODE` is set for every test run). Other build caches (e.g. compiled languages with incremental builds) should be fine because the test command rebuilds, but check the first run's report looks sensible.

## Real-world example

See [`case-studies/tomli/`](../case-studies/tomli/): Bug Vaccine run on the TOML parser that became Python's built-in `tomllib`.
