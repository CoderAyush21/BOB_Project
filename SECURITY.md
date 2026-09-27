# Security

Bug Vaccine reads a company's git history, runs its tests, rewrites its source files temporarily, and builds prompts for an AI assistant. Each of those is a place where something could go wrong, so this page lists what we protect against and how. Every item in "Protections" has an automated test in `tests/test_security.py` or `tests/test_rag.py`.

## Threat model

| Asset | Threat | Protection |
|---|---|---|
| Files outside the repo | A malicious `mutants.json` uses `"file": "../../.ssh/authorized_keys"`, an absolute path, or a symlink to write elsewhere | `run.safe_path()` resolves every path and refuses anything outside the repository. `bugvaccine.py check` reports it as UNSAFE. |
| CI runner and its token | A pull request edits `.bugvaccine/config.json` so CI runs an attacker's command | `pr` mode refuses (exit 3) when the PR changes the config, unless the command is passed explicitly with `--test` or a maintainer uses `--allow-config-change`. The GitHub workflow fixes the command in `TEST_CMD`. |
| CI workflow | Script injection via `${{ github.* }}` values | Values go through `env:`, never into `run:` scripts. Least-privilege `permissions`, `persist-credentials: false`, `pull_request` (not `pull_request_target`), and a job timeout. |
| Secrets in git history | Old API keys, passwords, tokens or private keys (for example an IBM Cloud API key committed then removed) leak into the dossier, the RAG index, the dashboard or a Bob prompt | `vaccine/redact.py` redacts known token formats (AWS, GitHub, Slack, JWT, private keys, credentials in URLs) and quoted or config-style `key/secret/password/token = value` assignments, everywhere text leaves the tool. `mine` reports how many it found, so you can rotate them. |
| Company code in the dashboard | The page sends data somewhere | A strict Content-Security-Policy: `default-src 'none'`, `connect-src 'none'`, and only the page's own script, pinned by its SHA-256 hash. By default no external requests are made at all; fonts are opt-in with `--web-fonts`. `no-referrer`. |
| Dashboard viewers | A tampered results or knowledge file injects HTML or script (XSS) | Embedded JSON escapes `<`, `>` and `&`. The page validates every loaded field (whitelisted statuses, numeric coercion) and escapes every string it renders. The CSP blocks any injected script anyway. |
| Pasted stack traces and code | Sensitive text left in the browser | The Debug lab never saves pasted text; older saved input is deleted on load. Only patterns you explicitly add are stored locally. |
| Availability | A regex with nested quantifiers such as `(a+)+` hangs the matcher (ReDoS) | `learn` rejects such regexes, the Debug lab refuses them in the teach form, and inputs are capped at 200 KB and 2,000 characters per line. |
| Pull request comments | Text from mutants breaks out of code blocks, injects HTML or @mentions people | All comment text is redacted, backticks and HTML are neutralised, and @mentions are defused. |
| Your code, when patching | An automatic fix rewrites code it shouldn't, or breaks the build | A recipe only runs on lines where that bug's own signature matches; `patch` is a dry run unless `--apply`; paths are contained to the repo; if the tests fail after patching, every file is restored; a fix only counts after a re-scan. |
| Commit guard | A guard that silently checks nothing gives false confidence | `guard install` refuses without a knowledge base; it never overwrites another tool's hook; it only reviews source files, not docs or Bug Vaccine's own knowledge files (whose examples are bugs on purpose). |
| Working tree | A crash leaves a mutated file behind | Every mutated file is restored in a `finally` block (including Ctrl+C), and `run` warns if files it will touch have uncommitted changes. |

## Things you still need to do

- **Treat the test command as code.** It runs through your shell with your permissions. Only run Bug Vaccine on repos and commands you trust, and in CI prefer an isolated runner.
- **Rotate anything that was redacted.** Redaction stops the secret spreading further, but if it was ever real it's already in git history.
- **Pin GitHub Actions to commit SHAs** in production.
- **Redaction is pattern-based.** It catches common formats, not every possible secret. Don't paste production credentials into the Debug lab.
- **RAG sends retrieved text to the assistant you paste the prompt into** (for example IBM Bob). The prompt is redacted, but review it before sharing outside your organisation.

## Reporting a vulnerability

Please open a private security advisory on the repository rather than a public issue.
