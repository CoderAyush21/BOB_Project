"""Bug Vaccine: one command for everything.

  python bugvaccine.py demo                          watch the full 8-step demo
  python bugvaccine.py init  <repo> --test "<cmd>"   set up Bug Vaccine in your repo
  python bugvaccine.py mine  <repo>                  bug-fix history -> dossier for Bob
  python bugvaccine.py check <repo>                  validate mutants (no tests run)
  python bugvaccine.py run   <repo> [--html] [--min-immunity N]
  python bugvaccine.py pr    <repo> [--base main]    PR mode: only files changed vs base
  python bugvaccine.py dashboard <repo>              interactive dashboard of all results
  python bugvaccine.py learn <repo> [<repo> ...]     teach the debugger your company's bug patterns
  python bugvaccine.py debug --error "<text>"        match an error/report against company bugs
  git diff main | python bugvaccine.py debug --diff -   review a PR's new lines against company bugs
  python bugvaccine.py index <repo> [<repo> ...]     RAG: index history, postmortems, patterns, docs
  python bugvaccine.py ask "<question or error>"     RAG: cited company sources + grounded Bob prompt

Per-repo state lives in <repo>/.bugvaccine/ :
  config.json   test command + paths          (commit it)
  PROMPT.md     the Bob prompt for this repo  (commit it)
  antigens.json, mutants.json                 (commit them; Bob writes them)
  results*, report*                           (git-ignored)
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vaccine"))

import mine  # noqa: E402
import run  # noqa: E402

STATE = ".bugvaccine"
GITIGNORE = "results*.json\nreport*.html\ndashboard*.html\npr-comment.md\nantigens-raw.md\n"


def state_dir(repo):
    return Path(repo) / STATE


def q(path):
    """Quote a path for a copy-pasteable command if it contains spaces."""
    s = str(path)
    return f'"{s}"' if " " in s else s


def cli_hint():
    """The command the user should type, based on how they launched this script."""
    try:
        rel = os.path.relpath(ROOT / "bugvaccine.py")
    except ValueError:            # different drive on Windows
        rel = str(ROOT / "bugvaccine.py")
    return f"python {q(rel)}"


def load_config(repo):
    cfg = state_dir(repo) / "config.json"
    if not cfg.exists():
        sys.exit(f"No {STATE}/config.json in {repo}. Run first:\n  {cli_hint()} init {q(repo)} --test \"<your test command>\"")
    return json.loads(cfg.read_text(encoding="utf-8"))


def repo_name(repo):
    """The project's name: config.json 'name' if set, else the folder name."""
    cfg = state_dir(repo) / "config.json"
    if cfg.exists():
        name = json.loads(cfg.read_text(encoding="utf-8")).get("name")
        if name:
            return name
    return Path(repo).resolve().name


def named_repos(specs):
    """Positional repo args, each 'path' or 'name=path'. Refuses duplicate names, which would
    otherwise merge two different projects' bug patterns into one."""
    out, seen = [], {}
    for spec in specs:
        name, sep, path = spec.partition("=")
        if not sep or not Path(path).exists() and Path(spec).exists():
            name, path = None, spec
        name = name or repo_name(path)
        if name in seen:
            sys.exit(f"Two repos are both called '{name}' ({seen[name]} and {path}).\n"
                     f"Give one a unique name, e.g.  {name}-billing={q(path)}  or set \"name\" in its {STATE}/config.json.")
        seen[name] = path
        out.append((name, path))
    return out


def mutants_path(repo, cfg, override=None):
    p = Path(override) if override else state_dir(repo) / cfg.get("mutants", "mutants.json")
    if not p.exists():
        sys.exit(f"No mutants file at {p}. Create it with Bob (see {STATE}/PROMPT.md), or pass --mutants.")
    return p


def warn_if_dirty(repo, files):
    out = subprocess.run(["git", "status", "--porcelain", "--", *files], cwd=repo,
                         capture_output=True, text=True).stdout.strip()
    if out:
        print("WARNING: files that will be mutated have uncommitted changes. They are restored after\n"
              "each mutant, but commit or stash first to be safe:\n  " + out.replace("\n", "\n  "))


# ── commands ────────────────────────────────────────────────────────────────

def cmd_demo(a):
    sys.exit(subprocess.call([sys.executable, str(ROOT / "prototype/run_prototype.py"), *(["--no-pause"] if a.no_pause else [])]))


def cmd_init(a):
    repo = Path(a.repo)
    if not (repo / ".git").exists():
        sys.exit(f"{repo} is not a git repository (Bug Vaccine needs its history).")
    d = state_dir(repo)
    d.mkdir(exist_ok=True)
    cfg = d / "config.json"
    if cfg.exists() and not a.force:
        sys.exit(f"{cfg} already exists (use --force to overwrite).")
    name = a.name or repo.resolve().name
    cfg.write_text(json.dumps({"name": name, "test": a.test, "timeout": a.timeout, "mutants": "mutants.json",
                               "min_immunity": a.min_immunity}, indent=2) + "\n", encoding="utf-8")
    # PROMPT.md is committed and shared, so it must not contain this machine's absolute path
    # (wrong for teammates, and it leaks a username). Use a path relative to the repo instead.
    try:
        rel = Path(os.path.relpath(ROOT / "bugvaccine.py", repo.resolve())).as_posix()
    except ValueError:           # tool on another drive: nothing portable to write
        rel = "<path-to-bug-vaccine>/bugvaccine.py"
    prompt = (ROOT / "bob-prompts/your-repo/PROMPT.md").read_text(encoding="utf-8")
    (d / "PROMPT.md").write_text(prompt.replace("{{BV}}", f"python {rel}").replace("{{TEST}}", a.test), encoding="utf-8")
    (d / ".gitignore").write_text(GITIGNORE, encoding="utf-8")

    print(f"Created {d}/ (config.json, PROMPT.md, .gitignore) for project '{name}'")
    print("Checking your test command passes on the unmodified code...")
    code, secs, output = run.run_tests(repo, a.test, a.timeout, with_output=True)
    if code != 0:
        hint = run.explain_failure(output)
        print(f"  FAILED (exit {code}). Last lines of output:\n    " + output.replace("\n", "\n    "))
        if hint:
            print(f"  {hint}")
        print(f"  Fix the command, then:  {cli_hint()} init {q(repo)} --test \"<command>\" --force")
        sys.exit(1)
    print(f"  OK in {secs:.1f}s. Each mutant costs about one test run, so 20 mutants ~ {20 * secs:.0f}s.")
    print(f"\nNext: open {q(repo)} in IBM Bob and paste {STATE}/PROMPT.md, or first run:\n  {cli_hint()} mine {q(repo)}")


def cmd_mine(a):
    out = a.out or str(state_dir(a.repo) / "antigens-raw.md")
    state_dir(a.repo).mkdir(exist_ok=True)
    mine.main([a.repo, "-o", out, "--max", str(a.max)])


def cmd_check(a):
    cfg = load_config(a.repo)
    spec = json.loads(mutants_path(a.repo, cfg, a.mutants).read_text(encoding="utf-8"))
    ids = {x["id"] for x in spec.get("antigens", [])}
    bad = 0
    for m in spec["mutants"]:
        problems = []
        missing = [k for k in ("id", "antigen", "file", "find", "replace") if k not in m]
        if missing:
            problems.append(f"missing fields {missing}")
        elif m["antigen"] not in ids:
            problems.append(f"unknown antigen {m['antigen']}")
        if not missing:
            try:
                path = run.safe_path(a.repo, m["file"])
            except ValueError as e:
                problems.append(f"UNSAFE: {e}")
                path = None
            if path is None:
                pass
            elif not path.is_file():
                problems.append(f"file not found: {m['file']}")
            else:
                _, hits = run.apply_mutant(run.read_source(path)[0], m["find"], m["replace"])
                if hits != 1:
                    problems.append(f"'find' matches {hits} times (need exactly 1)")
                if m["find"] == m["replace"]:
                    problems.append("'find' and 'replace' are identical")
        bad += bool(problems)
        print(f"  {m.get('id', '?'):<6} {'OK' if not problems else 'PROBLEM: ' + '; '.join(problems)}")
    print(f"\n{len(spec['mutants']) - bad}/{len(spec['mutants'])} mutants valid.")
    sys.exit(1 if bad else 0)


def run_args(a, cfg, extra):
    mp = mutants_path(a.repo, cfg, a.mutants)
    spec = json.loads(mp.read_text(encoding="utf-8"))
    warn_if_dirty(a.repo, sorted({m["file"] for m in spec["mutants"]}))
    d = state_dir(a.repo)
    argv = [str(mp), "--repo", a.repo, "--test", a.test or cfg["test"],
            "--timeout", str(cfg.get("timeout", 120)), "-o", str(d / a.out), *extra]
    gate = a.min_immunity if a.min_immunity is not None else cfg.get("min_immunity")
    if gate is not None:
        argv += ["--min-immunity", str(gate)]
    run.main(argv)


def cmd_run(a):
    cfg = load_config(a.repo)
    extra = []
    if a.html:
        extra += ["--html", str(state_dir(a.repo) / "report.html")]
    if a.compare:   # accept a bare name like results-before.json (looked up in .bugvaccine/)
        c = Path(a.compare)
        if not c.exists() and (state_dir(a.repo) / c).exists():
            c = state_dir(a.repo) / c
        if not c.exists():
            sys.exit(f"--compare file not found: {a.compare}")
        extra += ["--compare", str(c)]
    run_args(a, cfg, extra)


def cmd_pr(a):
    cfg = load_config(a.repo)
    # Security: in CI the test command runs with a token. If the PR itself edits the config, a malicious
    # PR could swap in any command. Refuse unless the command is given explicitly or a maintainer opts in.
    cfg_rel = f"{STATE}/config.json"
    if cfg_rel in run.changed_files(a.repo, a.base) and not (a.test or a.allow_config_change):
        print(f"REFUSED: this PR changes {cfg_rel}, which sets the command Bug Vaccine runs.\n"
              f"A maintainer should review that change, then re-run with --allow-config-change,\n"
              f"or CI should pass the test command explicitly with --test.")
        sys.exit(3)
    import debug
    d = state_dir(a.repo)
    test_cmd = a.test or cfg["test"]
    changed = run.changed_files(a.repo, a.base)
    mp = state_dir(a.repo) / cfg.get("mutants", "mutants.json")
    spec = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {"antigens": [], "mutants": []}
    mutants = [m for m in spec["mutants"] if m["file"] in changed]
    print(f"PR mode: {len(changed)} changed file(s) since {a.base}; {len(mutants)} stored mutant(s) apply")

    # Check 2: new lines against company bug history. Without this, a brand-new file that repeats
    # a known bug has no stored mutants and would look clean.
    kb = load_kb(a.repo, a.kb, spec)
    new_code = None
    if kb:
        diff = subprocess.run(["git", "diff", f"{a.base}...HEAD"], cwd=a.repo, capture_output=True,
                              text=True, encoding="utf-8", errors="replace").stdout
        new_code = debug.match_diff(diff, kb)
        print(f"New code: {len(new_code)} added line(s) match known company bugs")
    else:
        print("New code: not checked (no knowledge base; see --kb)")

    if mutants:
        warn_if_dirty(a.repo, sorted({m["file"] for m in mutants}))
        run.baseline_or_exit(a.repo, test_cmd, cfg.get("timeout", 120))
    results = run.run_mutants(mutants, Path(a.repo), test_cmd, cfg.get("timeout", 120))
    out = run.summarize(repo_name(a.repo), spec["antigens"], results, "pull request")
    out["new_code"] = [{k: v for k, v in f.items() if k != "antigen"} | {"title": f["antigen"].get("title")}
                       for f in new_code] if new_code is not None else None
    out["comment_md"] = run.render_markdown(out, new_code)
    (d / a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    (d / "pr-comment.md").write_text(out["comment_md"], encoding="utf-8")
    run.print_summary(out, d / a.out)
    print(f"Wrote {d / 'pr-comment.md'}")
    gate = a.min_immunity if a.min_immunity is not None else cfg.get("min_immunity")
    code = run.gate(out, gate) if gate is not None else 0
    if new_code and a.fail_on_new_risks:
        print(f"FAILED: {len(new_code)} added line(s) repeat known company bugs (--fail-on-new-risks).")
        code = code or 2
    sys.exit(code)


def load_kb(repo, kb_path, spec):
    """Knowledge base for new-code checks: --kb, else .bugvaccine/company-knowledge.json, else this
    repo's own bug patterns (if they have signatures)."""
    import debug
    for p in filter(None, [kb_path, state_dir(repo) / "company-knowledge.json"]):
        if Path(p).exists():
            return json.loads(Path(p).read_text(encoding="utf-8"))
    own = [a for a in spec.get("antigens", []) if a.get("signatures")]
    if own:
        name = repo_name(repo)
        return {"antigens": [{**x, "repo": name, "key": f"{name}:{x['id']}"} for x in own]}
    return None


def cmd_index(a):
    import rag
    chunks = []
    for name, repo in named_repos(a.repos):
        chunks += rag.chunks_from_repo(repo, name)
        d = state_dir(repo)
        f = next((d / n for n in ("antigens.json", "mutants.json") if (d / n).exists()), None)
        if f:
            chunks += rag.chunks_from_antigens(f, name)
    for s in a.source:
        name, _, path = s.partition("=")
        chunks += rag.chunks_from_antigens(path, name)
    if a.docs:
        chunks += rag.chunks_from_docs(a.docs)
    if not chunks:
        sys.exit("Nothing to index. Give repos, --source name=antigens.json, or --docs files.")
    index = rag.build_index(chunks)
    Path(a.out).write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    kinds = {}
    for c in index["chunks"]:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    print(f"Indexed {len(chunks)} chunks ({', '.join(f'{v} {k}' for k, v in sorted(kinds.items()))}) -> {a.out}")


def cmd_ask(a):
    import rag
    index = json.loads(Path(a.index).read_text(encoding="utf-8"))
    question = a.question if a.question != "-" else sys.stdin.read()
    kb = json.loads(Path(a.kb).read_text(encoding="utf-8")) if a.kb and Path(a.kb).exists() else None
    hits = rag.hybrid_search(question, index["chunks"], kb, a.k)
    if not hits:
        print("No company sources match. Try other words, or index more repos/docs.")
    for i, h in enumerate(hits, 1):
        c = h["chunk"]
        snippet = " ".join(c["text"].split())[:180]
        print(f"[{i}] {c['title']}\n    {c['kind']} | {c['ref']} | score {h['score']} | matched: {', '.join(h['matched'])}\n    {snippet}")
    if a.prompt:
        print("\n" + "=" * 72 + "\nGROUNDED PROMPT (paste into IBM Bob)\n" + "=" * 72)
        print(rag.grounded_prompt(question, hits))


def cmd_learn(a):
    import debug
    sources = []
    for name, repo in named_repos(a.repos):
        d = state_dir(repo)
        f = next((d / n for n in ("antigens.json", "mutants.json") if (d / n).exists()), None)
        if not f:
            sys.exit(f"No antigens in {d}. Run the Bob phases (Phase 1) on {repo} first.")
        sources.append((name, f))
    for s in a.source:
        name, _, path = s.partition("=")
        if not path:
            sys.exit(f"--source must look like name=path/to/antigens.json (got {s!r})")
        sources.append((name, Path(path)))
    if not sources:
        sys.exit("Give one or more repos, or --source name=file.")
    dupes = {n for n, _ in sources if [x for x, _ in sources].count(n) > 1}
    if dupes:
        sys.exit(f"Duplicate project name(s): {', '.join(sorted(dupes))}. Use name=path to tell them apart.")
    kb = debug.learn(sources)
    if a.merge and Path(a.out).exists():
        old = json.loads(Path(a.out).read_text(encoding="utf-8"))
        new_keys = {x["key"] for x in kb["antigens"]}
        kb["antigens"] = [x for x in old["antigens"] if x["key"] not in new_keys] + kb["antigens"]
        kb["sources"] = [s for s in old["sources"] if s["name"] not in {n for n, _ in sources}] + kb["sources"]
    Path(a.out).write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding="utf-8")
    for s in kb["sources"]:
        print(f"  {s['name']:<24} {s['antigens']} bug patterns, {s['with_signatures']} with debugging signatures")
    print(f"Knowledge base: {len(kb['antigens'])} bug patterns -> {a.out}")


def cmd_debug(a):
    import debug
    argv = ["--kb", a.kb]
    if a.error:
        argv += ["--error", a.error]
    if a.error_file:
        argv += ["--error-file", a.error_file]
    if a.scan:
        argv += ["--scan", *a.scan]
    if a.diff:
        argv += ["--diff", a.diff]
    if a.prompt:
        argv.append("--prompt")
    debug.main(argv)


def cmd_dashboard(a):
    import dashboard
    d = state_dir(a.repo)
    pick = lambda *names: next((str(d / n) for n in names if (d / n).exists()), None)
    argv = ["--repo", a.repo, "--title", f"Bug Vaccine: {Path(a.repo).resolve().name}", "-o", str(d / "dashboard.html")]
    found = {"before": pick("results-before.json", "results.json"), "after": pick("results-after.json"),
             "holdout": pick("results-holdout.json"), "pr": pick("results-pr.json")}
    if not any(found.values()):
        sys.exit(f"No results in {d}. Run `python bugvaccine.py run {a.repo}` first.")
    for k, v in found.items():
        if v:
            argv += [f"--{k}", v]
    if a.antibodies:
        argv += ["--antibodies", a.antibodies]
    if a.kb:
        argv += ["--knowledge", a.kb]
    if a.rag:
        argv += ["--rag", a.rag]
    if a.web_fonts:
        argv.append("--web-fonts")
    dashboard.main(argv)
    print("Using: " + ", ".join(k for k, v in found.items() if v))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("demo", help="run the full demo")
    p.add_argument("--no-pause", action="store_true")
    p.set_defaults(fn=cmd_demo)

    p = sub.add_parser("init", help="set up Bug Vaccine in a repo")
    p.add_argument("repo")
    p.add_argument("--test", required=True, help='e.g. "npm test --silent" or "pytest -q"')
    p.add_argument("--name", help="project name used across the company (default: folder name)")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--min-immunity", type=int, default=None, help="CI gate percentage (optional)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("mine", help="bug-fix history -> dossier for Bob")
    p.add_argument("repo")
    p.add_argument("-o", "--out")
    p.add_argument("--max", type=int, default=50)
    p.set_defaults(fn=cmd_mine)

    p = sub.add_parser("check", help="validate mutants without running tests")
    p.add_argument("repo")
    p.add_argument("--mutants")
    p.set_defaults(fn=cmd_check)

    for name, fn, helptext in (("run", cmd_run, "run the vaccine"), ("pr", cmd_pr, "PR mode")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("repo")
        p.add_argument("--mutants")
        p.add_argument("--test", help="override the configured test command")
        p.add_argument("--min-immunity", type=int)
        p.add_argument("-o", "--out", default="results.json" if name == "run" else "results-pr.json")
        if name == "run":
            p.add_argument("--html", action="store_true", help=f"write {STATE}/report.html")
            p.add_argument("--compare", help="earlier results.json for before/after")
        else:
            p.add_argument("--base", default="main")
            p.add_argument("--allow-config-change", action="store_true",
                           help="run even though this PR edits .bugvaccine/config.json (maintainers only)")
            p.add_argument("--kb", help="company knowledge base for checking new code "
                                        "(default: .bugvaccine/company-knowledge.json, else this repo's patterns)")
            p.add_argument("--fail-on-new-risks", action="store_true",
                           help="exit 2 if added lines repeat known company bugs")
        p.set_defaults(fn=fn)

    p = sub.add_parser("index", help="RAG: index fix commits, postmortems, bug patterns and docs")
    p.add_argument("repos", nargs="*", help="repos to index; use name=path to set the project name")
    p.add_argument("--source", action="append", default=[], metavar="NAME=FILE", help="extra antigens file")
    p.add_argument("--docs", nargs="*", help="extra Markdown/text docs (runbooks, READMEs)")
    p.add_argument("-o", "--out", default="rag-index.json")
    p.set_defaults(fn=cmd_index)

    p = sub.add_parser("ask", help="RAG: retrieve company sources for a question or error, with citations")
    p.add_argument("question", help="question, error or bug report ('-' reads stdin)")
    p.add_argument("--index", default="rag-index.json")
    p.add_argument("--kb", default="knowledge.json", help="knowledge base for hybrid (signature-boosted) retrieval")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--prompt", action="store_true", help="print a grounded prompt for Bob")
    p.set_defaults(fn=cmd_ask)

    p = sub.add_parser("dashboard", help="build the interactive dashboard from .bugvaccine/ results")
    p.add_argument("repo")
    p.add_argument("--antibodies", help="test file with your antibody tests (optional)")
    p.add_argument("--kb", help="company knowledge base to include in the Debug lab")
    p.add_argument("--rag", help="RAG index (bugvaccine.py index) for cited sources in the Debug lab")
    p.add_argument("--web-fonts", action="store_true", help="allow the page to load IBM Plex from Google Fonts")
    p.set_defaults(fn=cmd_dashboard)

    p = sub.add_parser("learn", help="teach the debugger: merge repos' bug patterns into a company knowledge base")
    p.add_argument("repos", nargs="*", help="repos with .bugvaccine/antigens.json; use name=path to set the project name")
    p.add_argument("--source", action="append", default=[], metavar="NAME=FILE", help="extra antigens file")
    p.add_argument("-o", "--out", default="knowledge.json")
    p.add_argument("--merge", action="store_true", help="add to an existing knowledge base instead of replacing it")
    p.set_defaults(fn=cmd_learn)

    p = sub.add_parser("debug", help="match an error, bug report or code against the company knowledge base")
    p.add_argument("--kb", default="knowledge.json")
    p.add_argument("--error", help="error message, stack trace or bug report")
    p.add_argument("--error-file")
    p.add_argument("--scan", nargs="*", help="files to scan for known risky code")
    p.add_argument("--diff", help="review a unified diff (only added lines); '-' reads stdin, e.g. git diff main | ... --diff -")
    p.add_argument("--prompt", action="store_true", help="also print a Bob debugging prompt")
    p.set_defaults(fn=cmd_debug)

    # Company docs contain any Unicode; a default Windows console (cp1252) can't print all of it.
    # Replace what it can't show instead of crashing.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
