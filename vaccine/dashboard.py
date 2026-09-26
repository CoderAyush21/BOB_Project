"""Build the interactive Bug Vaccine dashboard: one self-contained HTML file.

    python vaccine/dashboard.py --repo demo-repo --before results-before.json \
        --after results-after.json --holdout results-holdout.json --pr results-pr.json \
        --antibodies demo-repo/test/antibodies.test.js -o dashboard.html

Every input except --repo is optional; steps without data show as "not run yet".
The page works offline (fonts fall back to system faces without a connection).
"""
import argparse
import base64
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

import debug
import mine
import rag
import redact
from redact import redact_text

MAX_TIMELINE = 40
TEST_NAME = re.compile(r"""\btest\(\s*(['"`])(.+?)\1|\bdef\s+(test_\w+)""")


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8").stdout


def history(repo):
    log = git(repo, "log", "--reverse", "--format=%h\x1f%ad\x1f%s", "--date=short").splitlines()
    fix_shas = {sha[:7] for sha, *_ in mine.fix_commits(repo)}
    commits = []
    for line in log:
        sha, date, subject = line.split("\x1f")
        is_fix = sha[:7] in fix_shas
        tests = None
        if is_fix:
            files = git(repo, "show", "--name-only", "--format=", sha).split()
            tests = mine.touches_tests(files)
        commits.append({"sha": sha, "date": date, "subject": subject, "fix": is_fix, "tests": tests})
    shown = commits if len(commits) <= MAX_TIMELINE else [c for c in commits if c["fix"]][-MAX_TIMELINE:]
    incidents = []
    for path in mine.incident_docs(repo):
        text = (Path(repo) / path).read_text(encoding="utf-8", errors="replace")
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), path)
        open_items = [re.sub(r"\s*←.*$", "", l.split("]", 1)[1]).strip(" *")
                      for l in text.splitlines() if l.strip().startswith("- [ ]")]
        incidents.append({"path": path, "title": title, "open": open_items})
    return {"total": len(commits), "fixes": sum(c["fix"] for c in commits),
            "commits": shown, "truncated": len(shown) < len(commits), "incidents": incidents}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path and Path(path).exists() else None


def antibody_names(path):
    if not path or not Path(path).exists():
        return []
    text = Path(path).read_text(encoding="utf-8")
    return [m.group(2) or m.group(3) for m in TEST_NAME.finditer(text)]


def build(args):
    runs = {k: load(getattr(args, k)) for k in ("before", "after", "holdout", "pr")}
    antigens = {}
    for r in filter(None, runs.values()):
        for a in r["antigens"]:
            antigens.setdefault(a["id"], a)
    return {
        "meta": {"repo": Path(args.repo).resolve().name, "title": args.title,
                 "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M")},
        "history": history(args.repo),
        "antigens": list(antigens.values()),
        "runs": runs,
        "antibodies": antibody_names(args.antibodies),
        "knowledge": load(args.knowledge),
        "projects": projects(args.project) or [{"name": Path(args.repo).resolve().name,
                                                "before": runs["before"], "after": runs["after"]}],
        "samples": {"diff": sample(args.diff_sample)},
        "rag": (load(args.rag) or {}).get("chunks", []),
    }


def projects(specs):
    """--project NAME=BEFORE.json[,AFTER.json] -> [{name, before, after}] (results summaries)."""
    out = []
    for spec in specs or []:
        name, _, files = spec.partition("=")
        before, _, after = files.partition(",")
        out.append({"name": name, "before": load(before), "after": load(after) if after else None})
    return out


def sample(path):
    return Path(path).read_text(encoding="utf-8") if path and Path(path).exists() else None


FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
         '&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">')


def _redact_all(value):
    """Every string that goes into the page is secret-redacted first."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [_redact_all(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact_all(v) for k, v in value.items()}
    return value


def render(data, web_fonts=False):
    """Self-contained page with a strict CSP: no network access at all (unless web_fonts), and only
    the page's own script (pinned by hash) may run."""
    data = _redact_all(data)
    data["config"] = {   # the browser uses the same rules as the Python modules
        "redact": [[n, p, f, how] for n, p, f, how in redact.RULES],
        "nestedQuantifier": debug._NESTED_QUANTIFIER.pattern,
        "maxText": debug.MAX_TEXT, "maxLine": debug.MAX_LINE,
        "rag": {"stop": sorted(rag.STOP), "k1": rag.K1, "b": rag.B, "boost": rag.SIGNATURE_BOOST},
    }
    payload = (json.dumps(data, ensure_ascii=False)
               .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
    engine = (Path(__file__).parent / "web" / "engine.js").read_text(encoding="utf-8")
    page = (TEMPLATE.replace("__ENGINE__", engine).replace("__DATA__", payload)
            .replace("__TITLE__", html.escape(data["meta"]["title"]))
            .replace("__FONTS__", FONTS if web_fonts else ""))
    script = re.search(r"<script>([\s\S]*?)</script>", page).group(1)
    digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode()
    csp = "; ".join([
        "default-src 'none'",
        f"script-src 'sha256-{digest}'",
        "style-src 'unsafe-inline'" + (" https://fonts.googleapis.com" if web_fonts else ""),
        "font-src https://fonts.gstatic.com" if web_fonts else "font-src 'none'",
        "img-src data:", "connect-src 'none'", "form-action 'none'", "base-uri 'none'",
    ])
    return page.replace("__CSP__", csp)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    for k in ("before", "after", "holdout", "pr"):
        ap.add_argument(f"--{k}", help=f"results JSON for the {k} run")
    ap.add_argument("--antibodies", help="test file containing the antibody tests")
    ap.add_argument("--knowledge", help="company knowledge base (bugvaccine.py learn) for the Debug lab")
    ap.add_argument("--project", action="append", metavar="NAME=BEFORE.json[,AFTER.json]",
                    help="add a project to the Company view (repeatable)")
    ap.add_argument("--diff-sample", help="a unified diff to offer as a Debug lab example")
    ap.add_argument("--rag", help="RAG index (bugvaccine.py index) for cited company sources in the Debug lab")
    ap.add_argument("--web-fonts", action="store_true",
                    help="load IBM Plex from Google Fonts (off by default: the page makes no network requests)")
    ap.add_argument("--title", default="Bug Vaccine")
    ap.add_argument("-o", "--out", default="dashboard.html")
    args = ap.parse_args(argv)
    Path(args.out).write_text(render(build(args), web_fonts=args.web_fonts), encoding="utf-8")
    print(f"Wrote {args.out}")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="__CSP__">
<meta name="referrer" content="no-referrer">
<title>__TITLE__</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22 width=%2232%22 height=%2232%22 role=%22img%22 aria-label=%22Bug Vaccine%22%3E %3Cpath d=%22M16 1.5 28.5 5.5v10C28.5 23 23.5 28 16 30.8 8.5 28 3.5 23 3.5 15.5v-10Z%22 fill=%22%232456A6%22/%3E %3Ccircle cx=%2211.5%22 cy=%2211.5%22 r=%223.6%22 fill=%22%235BD394%22/%3E %3Ccircle cx=%2220.5%22 cy=%2211.5%22 r=%223.6%22 fill=%22%235BD394%22/%3E %3Ccircle cx=%2211.5%22 cy=%2220.3%22 r=%223.6%22 fill=%22%235BD394%22/%3E %3Ccircle cx=%2220.5%22 cy=%2220.3%22 r=%223.6%22 fill=%22%23FF8B7E%22/%3E %3C/svg%3E">
__FONTS__
<style>
:root{
  color-scheme:light;
  --bg:#EEF2F1; --surface:#FFFFFF; --surface-2:#F5F8F7; --ink:#15201E; --muted:#5C6B68; --line:#D8E0DE;
  --accent:#2456A6; --accent-soft:#E2EAF7; --on-accent:#FFFFFF;
  --caught:#1D7A4E; --caught-soft:#DCF0E4; --slipped:#B42A1F; --slipped-soft:#FAE2DE;
  --warn:#8F5500; --warn-soft:#FBEBD1; --idle:#C9D3D1;
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --cond:"IBM Plex Sans Condensed","Arial Narrow",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
  --r:10px;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  color-scheme:dark;
  --bg:#0E1413; --surface:#151D1C; --surface-2:#1A2423; --ink:#E3ECEA; --muted:#93A3A0; --line:#27322F;
  --accent:#8FB4F2; --accent-soft:#1C2940; --on-accent:#0E1413;
  --caught:#5BD394; --caught-soft:#12311F; --slipped:#FF8B7E; --slipped-soft:#3A1713;
  --warn:#F2B35B; --warn-soft:#382810; --idle:#34403E;
}}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#0E1413; --surface:#151D1C; --surface-2:#1A2423; --ink:#E3ECEA; --muted:#93A3A0; --line:#27322F;
  --accent:#8FB4F2; --accent-soft:#1C2940; --on-accent:#0E1413;
  --caught:#5BD394; --caught-soft:#12311F; --slipped:#FF8B7E; --slipped-soft:#3A1713;
  --warn:#F2B35B; --warn-soft:#382810; --idle:#34403E;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);font:15px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
[hidden]{display:none!important}
button{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
code,.mono{font-family:var(--mono);font-size:.86em}
h1,h2,h3{text-wrap:balance;margin:0}
.wrap{max-width:1240px;margin:0 auto;padding-inline:20px}

/* ── top bar ── */
.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;gap:14px;padding-block:12px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:600;font-size:17px}
.brand svg{flex:none}
.chip{font:500 12px/1 var(--mono);padding:6px 9px;border:1px solid var(--line);border-radius:99px;background:var(--surface);color:var(--muted)}
.spacer{flex:1}
.btn{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:var(--surface);border-radius:8px;
  padding:8px 14px;font-weight:500;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.btn.primary{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
.btn.primary:hover{filter:brightness(1.08)}

/* ── summary strip ── */
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;padding-block:18px}
.readout{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;display:grid;gap:6px}
.readout .label{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:500}
.readout .big{font:600 34px/1.05 var(--cond);font-variant-numeric:tabular-nums;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.readout .big small{font:500 15px var(--sans);color:var(--muted)}
.readout .arrow{color:var(--muted);font-size:22px}
.meter{height:6px;border-radius:99px;background:var(--idle);overflow:hidden;position:relative}
.meter i{position:absolute;inset:0 auto 0 0;background:var(--caught);border-radius:99px;transition:width .8s cubic-bezier(.2,.8,.2,1)}
.meter i.ghost{background:var(--slipped);opacity:.35}
.readout .note{font-size:13px;color:var(--muted)}
.hero-readout{grid-template-columns:auto 1fr;align-items:center;gap:16px;grid-column:span 2}
.hero-text{display:grid;gap:6px;min-width:0}
.ring{width:84px;height:84px;flex:none}
.ring circle{fill:none;stroke-linecap:round;transition:stroke-dasharray .9s cubic-bezier(.2,.8,.2,1)}
.ring-track{stroke:var(--idle);opacity:.55}
.ring-after{stroke:var(--caught)}
.ring-before{stroke:var(--slipped)}
.ring-num{font:600 13.5px var(--cond);fill:var(--ink)}
@media (max-width:1420px){#keys{display:none}}
@media (max-width:1180px){#repo{display:none}}
.good{color:var(--caught)} .bad{color:var(--slipped)} .warn{color:var(--warn)}

/* ── app layout ── */
.app{display:grid;grid-template-columns:250px minmax(0,1fr);gap:18px;padding-bottom:40px;align-items:start}
.rail{position:sticky;top:calc(env(safe-area-inset-top,0px) + 76px);display:grid;gap:4px;margin:0;padding:0;list-style:none}
.step{display:grid;grid-template-columns:28px 1fr;gap:10px;align-items:start;text-align:left;width:100%;border:1px solid transparent;
  background:none;border-radius:8px;padding:9px 10px;cursor:pointer;position:relative;overflow:hidden}
.step:hover{background:var(--surface)}
.step[aria-current="step"]{background:var(--surface);border-color:var(--line)}
.step .num{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font:600 13px var(--cond);
  border:1.5px solid var(--line);color:var(--muted);background:var(--surface)}
.step[aria-current="step"] .num{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.step.done .num{border-color:var(--caught);color:var(--caught)}
.step .t{font-weight:500;line-height:1.3}
.step .who{display:block;font-size:12px;color:var(--muted);margin-top:2px}
.step .who b{font-weight:600;color:var(--accent)}
.step.na{opacity:.5}
.step .prog{position:absolute;left:0;bottom:0;height:2px;background:var(--accent);width:0}
.step.playing .prog{animation:fill var(--dur,4.5s) linear forwards}
@keyframes fill{to{width:100%}}

.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:24px;min-height:420px}
.panel header{display:grid;gap:6px;margin-bottom:18px}
.eyebrow{font-size:12px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.tag{font:600 11px/1 var(--sans);letter-spacing:.04em;padding:4px 7px;border-radius:5px;background:var(--surface-2);border:1px solid var(--line);color:var(--muted);text-transform:none}
.tag.bob{background:var(--accent-soft);border-color:transparent;color:var(--accent)}
.panel h2{font-size:24px;font-weight:600;line-height:1.25}
.lede{color:var(--muted);max-width:68ch;margin:0}
.navrow{display:flex;justify-content:space-between;gap:10px;margin-top:22px;padding-top:16px;border-top:1px solid var(--line)}
.empty{padding:28px;border:1px dashed var(--line);border-radius:8px;color:var(--muted);text-align:center}

/* ── history timeline ── */
.timeline{list-style:none;margin:0;padding:0;display:grid}
.timeline li{display:grid;grid-template-columns:92px 16px 1fr;gap:12px;align-items:start;padding:7px 0}
.timeline .date{font:12px var(--mono);color:var(--muted);padding-top:2px;font-variant-numeric:tabular-nums}
.timeline .dot{width:10px;height:10px;border-radius:50%;background:var(--idle);margin-top:6px;justify-self:center;box-shadow:0 0 0 4px var(--surface)}
.timeline li.fix .dot{background:var(--warn)}
.timeline .subj{display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}
.timeline li:not(.fix) .subj{color:var(--muted)}
.pill{font:600 11px/1 var(--sans);padding:4px 8px;border-radius:99px;white-space:nowrap}
.pill.ok{background:var(--caught-soft);color:var(--caught)}
.pill.no{background:var(--slipped-soft);color:var(--slipped)}
.pill.warn{background:var(--warn-soft);color:var(--warn)}
.incident{margin-top:18px;border:1px solid var(--line);border-left:3px solid var(--warn);border-radius:8px;padding:14px 16px;background:var(--surface-2)}
.incident h3{font-size:15px;font-weight:600}
.incident ul{margin:8px 0 0;padding-left:18px}

/* ── antigen cards ── */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.card{border:1px solid var(--line);border-radius:8px;padding:14px 16px;display:grid;gap:8px;align-content:start;background:var(--surface)}
.card .id{font:600 12px var(--mono);color:var(--accent)}
.card h3{font-size:16px;font-weight:600;line-height:1.3}
.card .pattern{font-size:14px}
.card .src{font-size:12.5px;color:var(--muted)}
.card .flag{font-size:13px;color:var(--warn);background:var(--warn-soft);border-radius:6px;padding:6px 9px}

/* ── assay plate ── */
.plate{border:1px solid var(--line);border-radius:12px;background:var(--surface-2);padding:16px;display:grid;gap:10px}
.plate-head{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center}
.plate-title{font:600 13px var(--mono);color:var(--muted)}
.legend{display:flex;gap:14px;font-size:12.5px;color:var(--muted);flex-wrap:wrap}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:10px;height:10px;border-radius:50%;display:inline-block}
.prow{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:12px;align-items:center}
.prow .pl{font-size:13px;line-height:1.3}
.prow .pl b{font:600 12px var(--mono);color:var(--accent);margin-right:6px}
.wells{display:flex;gap:10px;flex-wrap:wrap}
.well{width:44px;height:44px;border-radius:50%;border:2px solid var(--line);background:var(--surface);cursor:pointer;display:grid;place-items:center;
  font:600 11px var(--mono);color:var(--muted);transition:background .5s,border-color .5s,color .5s,transform .15s}
.well:hover{transform:scale(1.08)}
.well.killed,.well.timeout{background:var(--caught-soft);border-color:var(--caught);color:var(--caught)}
.well.survived{background:var(--slipped-soft);border-color:var(--slipped);color:var(--slipped)}
.well.invalid{border-style:dashed}
.well.sel{box-shadow:0 0 0 3px var(--accent)}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--surface)}
.seg button{border:0;background:none;padding:6px 12px;cursor:pointer;font-size:13px}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--on-accent)}

/* ── mutant table ── */
.list{width:100%;border-collapse:collapse;margin-top:16px;font-size:14px}
.list th{text-align:left;font-size:12px;font-weight:500;color:var(--muted);padding:8px;border-bottom:1px solid var(--line)}
.list td{padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}
.list tr{cursor:pointer}
.list tbody tr:hover td{background:var(--surface-2)}
.scroll{overflow-x:auto}
.st{font:600 11.5px/1 var(--sans);padding:4px 8px;border-radius:99px;white-space:nowrap;display:inline-block}
.st.killed,.st.timeout{background:var(--caught-soft);color:var(--caught)}
.st.survived{background:var(--slipped-soft);color:var(--slipped)}
.st.invalid,.st.none{background:var(--surface-2);color:var(--muted);border:1px solid var(--line)}

/* ── antibodies ── */
.abs{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.abs li{display:grid;grid-template-columns:22px 1fr;gap:10px;align-items:start;padding:10px 12px;border:1px solid var(--line);border-radius:8px;font-family:var(--mono);font-size:13.5px}
.abs li::before{content:"+";font-weight:600;color:var(--caught)}
.callout{margin-top:14px;font-size:14px;color:var(--muted)}

/* ── PR comment ── */
.pr{border:1px solid var(--line);border-radius:8px;overflow:hidden;max-width:820px}
.pr-head{display:flex;gap:10px;align-items:center;padding:10px 14px;background:var(--surface-2);border-bottom:1px solid var(--line);font-size:13.5px;flex-wrap:wrap}
.pr-avatar{width:26px;height:26px;border-radius:50%;background:var(--accent);display:grid;place-items:center;color:var(--on-accent)}
.pr-body{padding:16px 18px;display:grid;gap:12px}
.pr-body h3{font-size:17px}
.risk{border:1px solid var(--line);border-radius:8px;padding:12px 14px;display:grid;gap:8px}
.diff{font:12.5px/1.55 var(--mono);border:1px solid var(--line);border-radius:6px;overflow-x:auto;background:var(--surface)}
.diff div{padding:1px 10px;white-space:pre}
.diff .d{background:var(--slipped-soft)} .diff .a{background:var(--caught-soft)}

/* ── drawer ── */
.scrim{position:fixed;inset:0;background:rgba(10,16,15,.35);z-index:9}
.drawer{position:fixed;top:0;right:0;bottom:0;width:min(460px,100%);background:var(--surface);border-left:1px solid var(--line);z-index:10;
  padding:calc(env(safe-area-inset-top,0px) + 20px) 22px calc(env(safe-area-inset-bottom,0px) + 20px);overflow-y:auto;display:grid;gap:14px;align-content:start;
  box-shadow:-12px 0 30px rgba(0,0,0,.12);transform:translateX(0);transition:transform .25s}
.drawer h3{font-size:19px;line-height:1.3}
.kv{display:grid;grid-template-columns:110px 1fr;gap:6px 12px;font-size:14px}
.kv dt{color:var(--muted)} .kv dd{margin:0}
.runs{display:flex;gap:8px;flex-wrap:wrap}
.close{justify-self:end}

/* ── tabs, theme ── */
.tabs{display:flex;gap:4px;background:var(--surface-2);border:1px solid var(--line);border-radius:9px;padding:3px}
.tabs button{border:0;background:none;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:500;color:var(--muted)}
.tabs button[aria-selected="true"]{background:var(--surface);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.icon-btn{border:1px solid var(--line);background:var(--surface);border-radius:8px;padding:7px 10px;cursor:pointer;font-size:13px;color:var(--muted)}
.hint{font-size:12px;color:var(--muted)}
kbd{font:500 11px var(--mono);border:1px solid var(--line);border-bottom-width:2px;border-radius:4px;padding:1px 5px;background:var(--surface)}

/* ── debug lab ── */
.lab{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:18px;padding-block:18px 40px;align-items:start}
.box{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:20px;display:grid;gap:14px;align-content:start}
.box h2{font-size:20px;font-weight:600}
.box h3{font-size:15px;font-weight:600}
.samples{display:flex;gap:6px;flex-wrap:wrap}
.samples button{border:1px solid var(--line);background:var(--surface-2);border-radius:99px;padding:5px 11px;font-size:13px;cursor:pointer}
.samples button:hover{border-color:var(--accent);color:var(--accent)}
textarea,input,select{font:13.5px/1.5 var(--mono);color:var(--ink);background:var(--surface-2);border:1px solid var(--line);border-radius:8px;padding:10px 12px;width:100%}
textarea{min-height:190px;resize:vertical}
textarea:focus,input:focus,select:focus{outline:2px solid var(--accent);outline-offset:0;border-color:transparent}
label{font-size:13px;font-weight:500;display:grid;gap:5px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.codeview{font:12.5px/1.6 var(--mono);border:1px solid var(--line);border-radius:8px;overflow-x:auto;background:var(--surface-2)}
.codeview div{display:grid;grid-template-columns:40px 1fr;white-space:pre}
.codeview .ln{color:var(--muted);text-align:right;padding-right:10px;user-select:none;border-right:1px solid var(--line)}
.codeview .src{padding-left:10px}
.codeview .hit{background:var(--slipped-soft)}
.codeview .hit .ln{color:var(--slipped);font-weight:600}
.match{border:1px solid var(--line);border-radius:10px;padding:16px;display:grid;gap:10px}
.match.known{border-left:3px solid var(--slipped)}
.match.maybe{border-left:3px solid var(--warn)}
.match h3{font-size:16px}
.match .reasons{display:grid;gap:6px;font-size:13.5px}
.match .reasons div{display:grid;grid-template-columns:78px 1fr;gap:8px}
.match .k{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding-top:2px}
.sect{display:grid;gap:4px;font-size:14px}
.sect b{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:500}
.prompt{font:12.5px/1.5 var(--mono);white-space:pre-wrap;background:var(--surface-2);border:1px solid var(--line);border-radius:8px;padding:12px;max-height:260px;overflow:auto;margin:0}
details.teach{border:1px solid var(--line);border-radius:10px;padding:0 16px;background:var(--surface)}
details.teach summary{cursor:pointer;font-weight:600;padding:14px 0}
details.teach[open]{padding-bottom:16px}
.teach-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.teach-grid .full{grid-column:1/-1}
.msg{font-size:13px}
.kb{width:100%;border-collapse:collapse;font-size:13.5px}
.kb th{text-align:left;font-size:12px;font-weight:500;color:var(--muted);padding:6px 8px;border-bottom:1px solid var(--line)}
.kb td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top}
.caption{display:flex;gap:12px;align-items:flex-start;margin:0 0 18px;padding:12px 14px;border-radius:8px;background:var(--accent-soft);
  color:var(--ink);font-size:15.5px;line-height:1.5;max-width:80ch}
.caption::before{content:"CC";font:600 10px/1 var(--mono);letter-spacing:.06em;color:var(--accent);border:1px solid var(--accent);border-radius:4px;padding:3px 4px;margin-top:3px;flex:none}
.recur{font:600 11px/1 var(--sans);padding:4px 8px;border-radius:99px;background:var(--warn-soft);color:var(--warn);white-space:nowrap}
textarea.drag{outline:2px dashed var(--accent);outline-offset:2px}
.difffile{font:600 12.5px var(--mono);padding:6px 10px;background:var(--surface);border-bottom:1px solid var(--line);display:block}
.company{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:18px;padding-block:18px 40px;align-items:start}
.bar{height:8px;border-radius:99px;background:var(--slipped-soft);overflow:hidden;min-width:90px}
.bar i{display:block;height:100%;background:var(--caught);border-radius:99px}
.inputs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.inputs input{font-family:var(--cond);font-size:18px;font-variant-numeric:tabular-nums}
.impact{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.impact .readout .big{font-size:28px}
.fine{font-size:12.5px;color:var(--muted);line-height:1.5}
.srcs{margin:0;padding:0;list-style:none;display:grid;gap:8px}
.srcs li{border:1px solid var(--line);border-radius:8px;padding:10px 12px;display:grid;gap:5px;font-size:14px;background:var(--surface-2)}
.srcs .snip{font-size:13px;color:var(--muted)}
.toast{position:fixed;bottom:calc(env(safe-area-inset-bottom,0px) + 20px);left:50%;transform:translateX(-50%);background:var(--ink);color:var(--bg);
  padding:9px 16px;border-radius:8px;font-size:14px;z-index:20}

@media (max-width:860px){
  .top{position:static}
  .hero-readout{grid-column:auto}
  .lab,.company{grid-template-columns:minmax(0,1fr)}
  .inputs,.impact{grid-template-columns:minmax(0,1fr)}
  .teach-grid{grid-template-columns:1fr}
  .top .hint{display:none}
  .app{grid-template-columns:minmax(0,1fr)}
  .summary{grid-template-columns:minmax(0,1fr)}
  .rail{position:static;display:flex;overflow-x:auto;gap:6px;padding-bottom:4px;scrollbar-width:thin}
  .rail li{flex:none}
  .step{grid-template-columns:24px auto;padding:8px 10px;border-color:var(--line);background:var(--surface)}
  .step .who{display:none}
  .panel{padding:18px}
  .prow{grid-template-columns:1fr}
  .timeline li{grid-template-columns:78px 14px 1fr}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<header class="top">
  <div class="wrap">
    <div class="brand">
      <svg width="30" height="30" viewBox="0 0 64 64" aria-hidden="true"><path d="M32 3.5 55 11v19.5C55 45 45.5 55 32 60.5 18.5 55 9 45 9 30.5V11Z" fill="var(--accent)"/><path d="M32 7.8 51.2 14v16.6c0 12.4-8 21-19.2 25.7C20.8 51.6 12.8 43 12.8 30.6V14Z" fill="var(--surface)"/><g fill="var(--caught)"><circle cx="22" cy="21.5" r="3.7"/><circle cx="32" cy="21.5" r="3.7"/><circle cx="42" cy="21.5" r="3.7"/><circle cx="22" cy="31.5" r="3.7"/><circle cx="42" cy="31.5" r="3.7"/><circle cx="22" cy="41.5" r="3.7"/><circle cx="32" cy="41.5" r="3.7"/><circle cx="42" cy="41.5" r="3.7"/></g><g transform="translate(32 31.8)"><path d="M-1.3-3.9-2.8-5.6M1.3-3.9 2.8-5.6" stroke="var(--slipped)" stroke-width="1.1" stroke-linecap="round" fill="none"/><ellipse cx="0" cy="0.4" rx="3.3" ry="4.1" fill="var(--slipped)"/><path d="M0-3.1V4.4" stroke="var(--surface)" stroke-width="0.9"/></g></svg>
      <span><b style="font-weight:700">Bug</b> Vaccine</span>
    </div>
    <div class="tabs" role="tablist" aria-label="Views">
      <button type="button" role="tab" id="tab-vaccine" data-view="vaccine" aria-selected="true">Vaccine run</button>
      <button type="button" role="tab" id="tab-debug" data-view="debug" aria-selected="false">Debug lab</button>
      <button type="button" role="tab" id="tab-company" data-view="company" aria-selected="false">Company</button>
    </div>
    <span class="chip" id="repo"></span>
    <span class="spacer"></span>
    <span class="hint" id="keys"><kbd>←</kbd> <kbd>→</kbd> steps · <kbd>Esc</kbd> close</span>
    <button class="icon-btn" id="cc" type="button" aria-pressed="false" title="Show narration for presenting or recording">Captions: off</button>
    <button class="icon-btn" id="theme" type="button" aria-label="Theme">Theme: auto</button>
    <button class="btn primary" id="play" type="button" aria-pressed="false"><span id="play-icon">▶</span> <span id="play-label">Play walkthrough</span></button>
  </div>
</header>

<main class="wrap">
  <div id="view-vaccine" role="tabpanel" aria-labelledby="tab-vaccine">
    <section class="summary" id="summary" aria-label="Results"></section>
    <div class="app">
      <ol class="rail" id="rail" aria-label="Steps"></ol>
      <article class="panel" id="panel" aria-live="polite"></article>
    </div>
  </div>
  <div id="view-debug" role="tabpanel" aria-labelledby="tab-debug" hidden>
    <div class="lab">
      <section class="box" aria-label="Your problem">
        <div class="eyebrow">Debug lab <span class="tag bob" id="kb-count"></span></div>
        <h2>What's going wrong?</h2>
        <p class="lede">Paste an error message, a stack trace, a customer bug report, some code or a pull request diff, or drop a file in the box. It is checked against every bug your company has already fixed.</p>
        <div class="samples" id="samples" aria-label="Examples"></div>
        <label for="dbg-input" style="display:flex;gap:6px;align-items:baseline">Error, report or code <span class="hint" id="dbg-lang"></span></label>
        <textarea id="dbg-input" spellcheck="false"></textarea>
        <div id="dbg-code" hidden></div>
        <details class="teach" id="teach">
          <summary>Teach it a new bug</summary>
          <div class="teach-grid">
            <label class="full" for="t-title">Name of the bug<input id="t-title" placeholder="Timezone dropped when saving dates"></label>
            <label class="full" for="t-pattern">What the mistake is<input id="t-pattern" placeholder="dates stored with toLocaleString() lose their timezone"></label>
            <label for="t-code">Risky code looks like (regex)<input id="t-code" placeholder="toLocaleString\("></label>
            <label for="t-error">The error or report looks like (regex)<input id="t-error" placeholder="wrong (time|hour)|timezone"></label>
            <label for="t-lang">Language<select id="t-lang"><option value="">any</option><option>javascript</option><option>python</option><option>java</option><option>go</option></select></label>
            <label for="t-fix">How it was fixed<input id="t-fix" placeholder="store ISO 8601 strings in UTC"></label>
          </div>
          <p class="msg" id="t-msg" aria-live="polite"></p>
          <div class="row"><button class="btn primary" type="button" id="t-add">Add to knowledge</button>
            <button class="btn" type="button" id="t-copy">Copy as JSON</button></div>
          <p class="hint">Added bugs are kept in this browser. To share them with the team, copy them as JSON, add them to a repo's <code>.bugvaccine/antigens.json</code> and run <code>bugvaccine.py learn --merge</code>.</p>
        </details>
      </section>
      <section class="box" aria-label="Matches" aria-live="polite" id="dbg-out"></section>
    </div>
    <section class="box" style="margin-bottom:40px" aria-label="Knowledge">
      <div class="row" style="justify-content:space-between"><h2>What it has learned</h2><span class="hint" id="kb-sources"></span></div>
      <div class="scroll" id="kb-table"></div>
    </section>
  </div>
  <div id="view-company" role="tabpanel" aria-labelledby="tab-company" hidden>
    <div class="company">
      <section class="box" aria-label="Projects">
        <div class="eyebrow">Company</div>
        <h2>Every project, one immunity score each</h2>
        <p class="lede">How well each project's tests would catch the bugs that project has already fixed.</p>
        <div class="scroll" id="projects"></div>
        <h3 style="margin-top:8px">Bugs fixed more than once</h3>
        <div id="recurring"></div>
      </section>
      <section class="box" aria-label="Impact estimate">
        <div class="eyebrow">Impact estimate <span class="tag">your assumptions</span></div>
        <h2>What regressions could cost</h2>
        <p class="lede">Change the numbers to match your team. Only the bug counts come from the measurements.</p>
        <div class="inputs">
          <label for="i-hours">Engineer hours per regression<input id="i-hours" type="number" min="0" step="0.5" value="6"></label>
          <label for="i-rate">Cost per engineer hour<input id="i-rate" type="number" min="0" step="5" value="100"></label>
          <label for="i-chance">Chance an unguarded bug returns in a year (%)<input id="i-chance" type="number" min="0" max="100" step="1" value="15"></label>
        </div>
        <div class="impact" id="impact"></div>
        <p class="fine" id="impact-note"></p>
      </section>
    </div>
  </div>
</main>
<div class="toast" id="toast" hidden role="status"></div>

<div class="scrim" id="scrim" hidden></div>
<aside class="drawer" id="drawer" hidden aria-label="Mutant details"></aside>

<script id="data" type="application/json">__DATA__</script>
<script>
__ENGINE__
const D = JSON.parse(document.getElementById('data').textContent);
const R = D.runs;
const CFG = D.config || {};

/* ── security: treat every loaded field as untrusted ── */
const STATUSES = new Set(['killed', 'timeout', 'survived', 'invalid']);
const num = v => Number.isFinite(+v) ? +v : 0;
function cleanRun(r){
  if (!r || typeof r !== 'object') return null;
  ['killed', 'total', 'immunity', 'timeouts', 'invalid'].forEach(k => r[k] = num(r[k]));
  r.antigens = Array.isArray(r.antigens) ? r.antigens : [];
  r.results = (Array.isArray(r.results) ? r.results : []).map(x => ({...x,
    id: String(x.id), antigen: String(x.antigen), file: String(x.file), find: String(x.find ?? ''), replace: String(x.replace ?? ''),
    status: STATUSES.has(x.status) ? x.status : 'invalid', seconds: num(x.seconds)}));
  r.new_code = Array.isArray(r.new_code) ? r.new_code.map(f => ({file: String(f.file), line: num(f.line), text: String(f.text),
    explain: String(f.explain), title: String(f.title || f.key)})) : null;
  r.comment_md = typeof r.comment_md === 'string' ? r.comment_md : null;
  return r;
}
['before', 'after', 'holdout', 'pr'].forEach(k => R[k] = cleanRun(R[k]));
D.projects = (D.projects || []).map(p => ({name: String(p.name), before: cleanRun(p.before), after: cleanRun(p.after)}));
D.history.total = num(D.history.total); D.history.fixes = num(D.history.fixes);
D.antibodies = (D.antibodies || []).map(String);
D.rag = (D.rag || []).map((c, i) => ({id: num(c.id) || i + 1, kind: String(c.kind), repo: String(c.repo), ref: String(c.ref), title: String(c.title), text: String(c.text)}));

const {redactText, riskyRegex, rx, detectLang, matchText, ragSearch, isDiff, parseDiff, matchDiff, MAX_TEXT, MAX_LINE} =
  BugVaccineEngine.create({getKb: () => kb(), rag: D.rag, config: CFG});   // vaccine/web/engine.js
try { localStorage.removeItem('bv-input'); } catch (e) {}   // older versions saved pasted text; never keep it
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const AG = Object.fromEntries(D.antigens.map(a => [a.id, a]));
const STATUS = {killed:'caught', timeout:'caught (timeout)', survived:'slipped through', invalid:'stale', none:'not run'};

const STEPS = [
  {key:'history', title:'Mine history', who:'tool', has:() => D.history.total > 0,
   what:'Read the git history and incident reports for bugs this project has already fixed, and check which fixes shipped with a test.'},
  {key:'antigens', title:'Extract bug patterns', who:'Bob · document understanding', has:() => D.antigens.length > 0,
   what:'Turn each fix into an antigen: the reusable pattern behind the bug, not the line that changed.'},
  {key:'hunt', title:'Hunt for re-entry points', who:'Bob · parallel subagents', has:() => !!R.before,
   what:'One subagent per pattern searches today\'s code for every place that bug could come back, including code written after the fix.'},
  {key:'before', title:'Re-infect', who:'tool', has:() => !!R.before,
   what:'Put each old bug back, one at a time, and run the test suite. Tests fail: caught. Tests pass: the bug could return unnoticed.'},
  {key:'antibodies', title:'Write antibodies', who:'Bob · agent mode', has:() => D.antibodies.length > 0,
   what:'Add tests that guard each pattern across many inputs. Production code is not touched.'},
  {key:'after', title:'Prove it', who:'tool', has:() => !!R.after,
   what:'Re-inject the same bugs against the new tests.'},
  {key:'holdout', title:'Blind check', who:'Bob · fresh subagent', has:() => !!R.holdout,
   what:'New variations of the same bugs, written without seeing the tests. This shows whether the tests guard the pattern or only memorised the first mutants.'},
  {key:'pr', title:'Review a pull request', who:'tool + Bob', has:() => !!R.pr,
   what:'On a pull request, check only the changed files and warn the reviewer if new code repeats a bug the project has already shipped.'},
];

const n = (r, k) => r ? r[k] : '?';
const SAY = {
  history: () => `Every team fixes bugs. The question is whether those fixes stay fixed. We start from this project's own history: ${D.history.fixes} bug fixes${D.history.incidents.length ? ' and an incident report' : ''}.`,
  antigens: () => `Bob reads each fix and the incident report, and names the pattern behind the bug, not just the line that changed.`,
  hunt: () => `One Bob subagent per pattern searches today's code for every place that bug could come back, including code written after the fix.`,
  before: () => `We put each old bug back, one at a time, and run the tests. Only ${n(R.before,'killed')} of ${n(R.before,'total')} are caught. The rest could come back and every test would still pass.`,
  antibodies: () => `Bob writes tests that guard each pattern across many inputs. The product code is not touched.`,
  after: () => `Same bugs, new tests: now ${n(R.after,'killed')} of ${n(R.after,'total')} are caught. Every number here comes from actually running the tests.`,
  holdout: () => `Were the tests just memorising? A fresh subagent that never saw them invents new variants of the same bugs. ${n(R.holdout,'killed')} of ${n(R.holdout,'total')} are caught.`,
  pr: () => { const k = R.pr ? prProblems(R.pr) : 0;
    return `Where it matters most: a pull request. Only the changed files are checked, and this one repeats ${k} bug${k === 1 ? '' : 's'} the project has already shipped. The reviewer sees it before merge.`; },
};
const prProblems = p => p.results.filter(x => x.status === 'survived').length + (p.new_code ? p.new_code.length : 0);
let cur = 0, playing = false, timer = null, plateRun = null, selected = null, captions = false;
const recurCount = a => ((a.source_commit || '').match(/\b[0-9a-f]{7,40}\b/g) || []).length;
const recurBadge = a => recurCount(a) > 1 ? `<span class="recur">fixed ${recurCount(a)} times</span>` : '';

/* ── summary ── */
function readout(label, bigHtml, meterHtml, note){
  return `<div class="readout"><span class="label">${label}</span><div class="big">${bigHtml}</div>${meterHtml}<span class="note">${note}</span></div>`;
}
/* immunity ring: outer arc = after (green), inner arc = before (red); drawn to scale (100% = full circle) */
function ring(before, after){
  const arc = (r, pct, cls, w) => { const c = 2 * Math.PI * r, len = Math.max(0, Math.min(100, pct)) / 100 * c;
    return `<circle cx="40" cy="40" r="${r}" class="ring-track" stroke-width="${w}"/>` +
      `<circle cx="40" cy="40" r="${r}" class="${cls}" stroke-width="${w}" stroke-dasharray="${len.toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 40 40)"/>`; };
  const shown = after ?? before;
  return `<svg class="ring" viewBox="0 0 80 80" role="img" aria-label="${after != null ? `immunity ${before}% before, ${after}% after` : `immunity ${before}%`}">
    ${after != null ? arc(33, after, 'ring-after', 7) + arc(23, before, 'ring-before', 5) : arc(33, before, before >= 90 ? 'ring-after' : 'ring-before', 7)}
    <text x="40" y="44" text-anchor="middle" class="ring-num">${shown}%</text></svg>`;
}
function meter(p, ghost){ return `<div class="meter">${ghost != null ? `<i class="ghost" style="width:100%"></i>` : ''}<i style="width:${p ?? 0}%"></i></div>`; }
function renderSummary(){
  const b = R.before, a = R.after, h = R.holdout, p = R.pr;
  const out = [];
  if (b) out.push(`<div class="readout hero-readout">${ring(b.immunity, a ? a.immunity : null)}<div class="hero-text">
    <span class="label">Past bugs caught by tests</span>
    <div class="big">${a ? `<span class="bad">${b.immunity}%</span><span class="arrow">→</span><span class="good">${a.immunity}%</span>`
      : `<span class="${b.immunity >= 90 ? 'good' : 'bad'}">${b.immunity}%</span>`}<small>${(a || b).killed}/${(a || b).total}</small></div>
    <span class="note">${a ? `${a.killed - b.killed} old bugs can no longer return unnoticed` : `${b.total - b.killed} could return unnoticed`}</span></div></div>`);
  if (h) out.push(readout('Blind check', `<span class="${h.immunity >= 90 ? 'good' : 'warn'}">${h.immunity}%</span><small>${h.killed}/${h.total}</small>`,
    meter(h.immunity, 1), 'new bug variants the tests were not written against'));
  if (p) { const risky = prProblems(p);
    out.push(readout('Pull request review', `<span class="${risky ? 'bad' : 'good'}">${risky}</span><small>${risky === 1 ? 'old bug' : 'old bugs'} sneaking back</small>`,
      '', `${p.total} checks in the files this PR changed`)); }
  out.push(readout('History read', `${D.history.fixes}<small>fixes in ${D.history.total} commits</small>`, '',
    D.history.incidents.length ? `${D.history.incidents.length} incident report${D.history.incidents.length > 1 ? 's' : ''}` : 'no incident reports found'));
  $('#summary').innerHTML = out.join('');
}

/* ── rail ── */
function renderRail(){
  $('#rail').innerHTML = STEPS.map((s, i) => `<li><button class="step ${s.has() ? '' : 'na'} ${i < cur ? 'done' : ''} ${playing && i === cur ? 'playing' : ''}"
     type="button" data-i="${i}" ${i === cur ? 'aria-current="step"' : ''}>
     <span class="num">${i + 1}</span><span><span class="t">${esc(s.title)}</span>
     <span class="who">${s.who.startsWith('Bob') ? `<b>${esc(s.who)}</b>` : esc(s.who)}</span></span><span class="prog"></span></button></li>`).join('');
  $('#rail').querySelectorAll('.step').forEach(b => b.onclick = () => { stop(); go(+b.dataset.i); });
}

/* ── plate ── */
function plate(run, opts = {}){
  if (!run) return `<div class="empty">This step hasn't been run yet.</div>`;
  const rows = {};
  run.results.forEach(m => (rows[m.antigen] ||= []).push(m));
  const toggle = opts.toggle ? `<div class="seg" role="group" aria-label="Show run">${opts.toggle.map(([k, l]) =>
      `<button type="button" data-run="${k}" aria-pressed="${k === opts.active}">${l}</button>`).join('')}</div>` : '';
  return `<div class="plate">
    <div class="plate-head"><span class="plate-title">${esc(opts.title || 'assay plate')} · ${run.killed}/${run.total} caught</span>${toggle}</div>
    ${Object.entries(rows).map(([ag, ms]) => `<div class="prow"><div class="pl"><b>${esc(ag)}</b>${esc(AG[ag]?.title || '')}</div>
      <div class="wells">${ms.map(m => `<button type="button" class="well ${m.status} ${selected === m.id ? 'sel' : ''}" data-m="${esc(m.id)}" data-run="${opts.runKey}"
        aria-label="${esc(m.id)}: ${STATUS[m.status]} in ${esc(m.file)}" title="${esc(m.id)} · ${STATUS[m.status]} · ${esc(m.file)}">${esc(m.id)}</button>`).join('')}</div></div>`).join('')}
    <div class="legend"><span><i style="background:var(--caught)"></i>caught by tests</span><span><i style="background:var(--slipped)"></i>slipped through</span><span>Select a well for details</span></div>
  </div>`;
}
function table(run, runKey, compare){
  return `<div class="scroll"><table class="list"><thead><tr>${compare ? '<th>Before</th>' : ''}<th>${compare ? 'After' : 'Result'}</th><th>Bug</th><th>Where</th></tr></thead><tbody>
  ${run.results.map(m => `<tr data-m="${esc(m.id)}" data-run="${runKey}" tabindex="0">
     ${compare ? `<td><span class="st ${statusIn(compare, m.id)}">${STATUS[statusIn(compare, m.id)]}</span></td>` : ''}
     <td><span class="st ${m.status}">${STATUS[m.status]}</span></td>
     <td><b class="mono">${esc(m.id)}</b> ${esc(AG[m.antigen]?.title || m.antigen)}<div class="note" style="color:var(--muted);font-size:13px">${esc(m.why || '')}</div></td>
     <td class="mono">${esc(m.file)}</td></tr>`).join('')}
  </tbody></table></div>`;
}
const statusIn = (run, id) => run?.results.find(x => x.id === id)?.status || 'none';

/* ── step panels ── */
const PANELS = {
  history(){
    const h = D.history;
    const items = h.commits.map(c => `<li class="${c.fix ? 'fix' : ''}"><span class="date">${esc(c.date)}</span><span class="dot"></span>
      <span class="subj"><span>${esc(c.subject)}</span>${c.fix ? (c.tests ? '<span class="pill ok">test added</span>' : '<span class="pill no">no test</span>') : ''}</span></li>`).join('');
    const inc = h.incidents.map(i => `<div class="incident"><h3>${esc(i.title)}</h3><span class="mono" style="color:var(--muted)">${esc(i.path)}</span>
      ${i.open.length ? `<ul>${i.open.map(o => `<li><span class="pill warn">never done</span> ${esc(o)}</li>`).join('')}</ul>` : ''}</div>`).join('');
    return `<ol class="timeline">${items}</ol>${h.truncated ? `<p class="callout">Showing the most recent bug-fix commits out of ${h.total}.</p>` : ''}${inc}`;
  },
  antigens(){
    return `<div class="grid">${D.antigens.map(a => `<div class="card"><div class="row"><span class="id">${esc(a.id)}</span>${recurBadge(a)}</div><h3>${esc(a.title)}</h3>
      <div class="pattern">${esc(a.pattern || '')}</div>
      ${a.source_commit ? `<div class="src">Fixed in: ${esc(a.source_commit)}</div>` : ''}
      ${(a.unfinished_followups || []).map(f => `<div class="flag">Postmortem follow-up never done: ${esc(f)}</div>`).join('')}</div>`).join('')}</div>`;
  },
  hunt(){
    const byFile = {};
    R.before.results.forEach(m => (byFile[m.file] ||= []).push(m));
    return `<div class="grid">${Object.entries(byFile).map(([f, ms]) => `<div class="card"><span class="id">${esc(f)}</span>
      <h3>${ms.length} re-entry point${ms.length > 1 ? 's' : ''}</h3>
      ${ms.map(m => `<div class="pattern"><b class="mono">${esc(m.id)}</b> ${esc(m.why || AG[m.antigen]?.title)}</div>`).join('')}</div>`).join('')}</div>`;
  },
  before(){ return plate(R.before, {title:'before vaccination', runKey:'before'}) + table(R.before, 'before'); },
  antibodies(){
    return `<ul class="abs">${D.antibodies.map(n => `<li>${esc(n)}</li>`).join('')}</ul>
      <p class="callout">${D.antibodies.length} tests added. The code under test was not changed.</p>`;
  },
  after(){
    const active = plateRun || 'after';
    return plate(R[active], {title: active === 'after' ? 'after vaccination' : 'before vaccination', runKey: active,
      toggle:[['before','Before'],['after','After']], active}) + table(R.after, 'after', R.before);
  },
  holdout(){ return plate(R.holdout, {title:'blind check', runKey:'holdout'}) + table(R.holdout, 'holdout'); },
  pr(){
    // Same two checks, and the same rule, as run.render_markdown: never a green result for unchecked code
    const p = R.pr, risky = p.results.filter(x => x.status === 'survived'), nc = p.new_code;
    const problems = risky.length + (nc ? nc.length : 0);
    const head = problems ? `⚠ ${problems} past bug${problems > 1 ? 's' : ''} could come back in this PR`
      : (!p.results.length && !nc) ? 'ℹ Nothing in this PR could be checked' : '✓ No known bugs found in this PR';
    const newCode = nc === null ? `<p class="hint">New code wasn't checked: no company knowledge base was available.</p>`
      : nc.length ? `<p>Lines this PR adds match bugs the company has already fixed:</p>${nc.map(f => `<div class="risk">
          <div><code>${esc(f.file)}:${f.line}</code> <b>${esc(f.title)}</b></div><div class="diff"><div class="a">+ ${esc(f.text)}</div></div>
          <div style="color:var(--muted);font-size:14px">${esc(f.explain)}</div></div>`).join('')}`
      : '<p>No added line matches a known company bug.</p>';
    const tests = !p.results.length ? '<p>No stored checks cover the files this PR changes.</p>'
      : risky.length ? `<p>${p.killed}/${p.total} caught. These past bugs could return and no test would notice:</p>
        ${risky.map(x => { const a = AG[x.antigen] || {};
          return `<div class="risk"><div><b>${esc(a.title || x.antigen)}</b> in <code>${esc(x.file)}</code></div>
            <div style="color:var(--muted);font-size:14px">${esc(x.why || '')}</div>${diff(x)}
            ${a.postmortem ? `<div style="font-size:13px;color:var(--muted)">Past incident: <code>${esc(a.postmortem)}</code></div>` : ''}</div>`; }).join('')}
        <p style="margin:0">Suggested: add a test that fails when the change above is applied.</p>`
      : `<p>${p.killed}/${p.total} caught. Every stored check that applies is covered by a test.</p>`;
    return `<div class="pr"><div class="pr-head"><span class="pr-avatar">✚</span><b>bug-vaccine</b><span style="color:var(--muted)">commented on this pull request</span></div>
      <div class="pr-body"><h3 class="${problems ? 'bad' : nc === null && !p.results.length ? '' : 'good'}">${head}</h3>
      <div class="sect"><b>New code vs. company bug history</b></div>${newCode}
      <div class="sect"><b>Tests vs. past bugs in the changed files</b></div>${tests}</div></div>
      <div class="row" style="margin-top:12px"><button class="btn" type="button" id="copy-pr">Copy comment as Markdown</button></div>`;
  },
};
function diff(m){
  return `<div class="diff">${m.find.split('\n').map(l => `<div class="d">- ${esc(l)}</div>`).join('')}${m.replace.split('\n').map(l => `<div class="a">+ ${esc(l)}</div>`).join('')}</div>`;
}

function renderPanel(){
  const s = STEPS[cur];
  const bob = s.who.startsWith('Bob') || s.who.includes('Bob');
  const content = s.has() ? PANELS[s.key]() : `<div class="empty">This step hasn't been run yet.</div>`;
  const cap = (captions || playing) && s.has() ? `<p class="caption">${esc(SAY[s.key]())}</p>` : '';
  $('#panel').innerHTML = `<header><div class="eyebrow">Step ${cur + 1} of ${STEPS.length} <span class="tag ${bob ? 'bob' : ''}">${esc(s.who)}</span></div>
    <h2>${esc(s.title)}</h2><p class="lede">${esc(s.what)}</p></header>${cap}${content}
    <div class="navrow"><button class="btn" type="button" id="prev" ${cur === 0 ? 'disabled' : ''}>← Previous</button>
    <button class="btn" type="button" id="next" ${cur === STEPS.length - 1 ? 'disabled' : ''}>Next →</button></div>`;
  $('#prev').onclick = () => { stop(); go(cur - 1); };
  $('#next').onclick = () => { stop(); go(cur + 1); };
  $('#panel').querySelectorAll('[data-m]').forEach(el => {
    const open = () => openDrawer(el.dataset.run, el.dataset.m);
    el.onclick = open;
    el.onkeydown = e => { if (e.key === 'Enter') open(); };
  });
  $('#panel').querySelectorAll('.seg button').forEach(b => b.onclick = () => { stop(); plateRun = b.dataset.run; renderPanel(); });
  if ($('#copy-pr')) $('#copy-pr').onclick = () => copy(R.pr.comment_md || prMarkdown(), 'PR comment copied');
}
function prMarkdown(){
  const p = R.pr, risky = p.results.filter(x => x.status === 'survived');
  const lines = [`### Bug Vaccine: ${risky.length ? '⚠️' : '✅'} ${p.killed}/${p.total} past bug patterns caught by tests`, ''];
  if (!risky.length) lines.push('Every known bug pattern that applies to this PR is caught by the test suite.');
  else {
    lines.push('This PR adds code where a bug **this repo has already shipped** could return, and no test would catch it:', '');
    // same neutralising as run.py md(): no fence/backtick breakouts, no raw HTML, no @mentions
    const mdt = s => redactText(String(s).replace(/[\r\n]+/g, ' '))[0].replace(/`/g, "'").replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/@(?=[A-Za-z0-9])/g, '@​');
    const mdc = s => redactText(String(s).split('\n')[0])[0].replace(/`/g, "'");
    risky.forEach(x => { const a = AG[x.antigen] || {};
      lines.push(`- **${mdt(a.title || x.antigen)}** in \`${mdc(x.file)}\`: ${mdt(x.why || '')}`, '  ```diff', `  - ${mdc(x.find)}`, `  + ${mdc(x.replace)}`, '  ```');
      if (a.postmortem) lines.push(`  Past incident: \`${mdc(a.postmortem)}\``); });
    lines.push('', 'Suggested: add a test that fails when the change above is applied.');
  }
  return lines.join('\n');
}

/* ── drawer ── */
function openDrawer(runKey, id){
  const m = R[runKey].results.find(x => x.id === id), a = AG[m.antigen] || {};
  selected = id;
  const runs = ['before','after','holdout','pr'].filter(k => R[k] && R[k].results.some(x => x.id === id))
    .map(k => `<span class="st ${statusIn(R[k], id)}">${k}: ${STATUS[statusIn(R[k], id)]}</span>`).join('');
  $('#drawer').innerHTML = `<button class="btn close" type="button" id="close">Close</button>
    <div class="eyebrow">Mutant <b class="mono">${esc(m.id)}</b></div>
    <h3>${esc(a.title || m.antigen)}</h3><p class="lede">${esc(m.why || '')}</p>
    <div class="runs">${runs}</div>
    <dl class="kv"><dt>Pattern</dt><dd>${esc(a.pattern || '')}</dd><dt>File</dt><dd class="mono">${esc(m.file)}</dd>
      ${a.source_commit ? `<dt>Original fix</dt><dd>${esc(a.source_commit)}</dd>` : ''}
      ${a.postmortem ? `<dt>Incident</dt><dd class="mono">${esc(a.postmortem)}</dd>` : ''}</dl>
    <div><div class="eyebrow" style="margin-bottom:6px">Injected change</div>${diff(m)}</div>`;
  $('#drawer').hidden = false; $('#scrim').hidden = false;
  $('#close').focus();
  $('#close').onclick = closeDrawer;
  document.querySelectorAll('.well').forEach(w => w.classList.toggle('sel', w.dataset.m === id));
}
function closeDrawer(){ $('#drawer').hidden = true; $('#scrim').hidden = true; selected = null;
  document.querySelectorAll('.well.sel').forEach(w => w.classList.remove('sel')); }
$('#scrim').onclick = closeDrawer;

/* ── navigation & play ── */
function go(i){
  cur = Math.max(0, Math.min(STEPS.length - 1, i));
  if (STEPS[cur].key !== 'after') plateRun = null;
  renderRail(); renderPanel();
  try { history.replaceState(null, '', '#step-' + (cur + 1)); } catch (e) {}
}
const DUR = 4500;
function tick(){
  if (!playing) return;
  const s = STEPS[cur];
  if (s.key === 'after' && R.before && plateRun !== 'after') {
    // show the plate flip: before, then after
    plateRun = 'before'; renderPanel();
    timer = setTimeout(() => { plateRun = 'after'; renderPanel(); timer = setTimeout(advance, DUR - 1500); }, 1500);
    return;
  }
  timer = setTimeout(advance, DUR);
}
function advance(){
  if (cur >= STEPS.length - 1) return stop();
  go(cur + 1); tick();
}
function start(){
  closeDrawer(); playing = true;
  if (cur >= STEPS.length - 1) cur = 0;
  document.documentElement.style.setProperty('--dur', DUR + 'ms');
  $('#play').setAttribute('aria-pressed', 'true'); $('#play-icon').textContent = '❚❚'; $('#play-label').textContent = 'Pause';
  go(cur); tick();
}
function stop(){
  playing = false; clearTimeout(timer);
  $('#play').setAttribute('aria-pressed', 'false'); $('#play-icon').textContent = '▶'; $('#play-label').textContent = 'Play walkthrough';
  renderRail();
}
$('#play').onclick = () => playing ? stop() : start();
document.addEventListener('keydown', e => {
  if (e.target.closest('input,textarea,select')) return;
  if (e.key === 'Escape') closeDrawer();
  if (view !== 'vaccine' || !$('#drawer').hidden) return;
  if (e.key === 'ArrowRight') { stop(); go(cur + 1); }
  if (e.key === 'ArrowLeft') { stop(); go(cur - 1); }
});

/* ── shared helpers ── */
function toast(msg){ const t = $('#toast'); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => t.hidden = true, 1800); }
function copy(text, msg){
  const done = () => toast(msg);
  const fallback = () => { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { toast('Select the text and copy it manually'); } ta.remove(); };
  try { navigator.clipboard.writeText(text).then(done, fallback); } catch (e) { fallback(); }
}
const store = {
  get(k, d){ try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
  set(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
};

/* ── theme ── */
const THEMES = ['auto', 'light', 'dark'];
let theme = store.get('bv-theme', 'auto');
function applyTheme(){
  if (theme === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', theme);
  $('#theme').textContent = 'Theme: ' + theme;
}
$('#theme').onclick = () => { theme = THEMES[(THEMES.indexOf(theme) + 1) % 3]; store.set('bv-theme', theme); applyTheme(); };

/* ── views ── */
let view = 'vaccine';
function showView(v){
  view = v;
  document.querySelectorAll('.tabs button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.view === v)));
  ['vaccine', 'debug', 'company'].forEach(k => $('#view-' + k).hidden = v !== k);
  ['#play', '#keys', '#cc'].forEach(id => $(id).hidden = v !== 'vaccine');
  if (v !== 'vaccine') { stop(); closeDrawer(); try { history.replaceState(null, '', '#' + v); } catch (e) {} }
  else go(cur);
}
$('#cc').onclick = () => { captions = !captions; $('#cc').setAttribute('aria-pressed', String(captions));
  $('#cc').textContent = 'Captions: ' + (captions ? 'on' : 'off'); renderPanel(); };
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => showView(b.dataset.view));

/* ── debug engine (mirrors vaccine/debug.py) ── */
const KB0 = D.knowledge ? D.knowledge.antigens : [];
let custom = store.get('bv-custom', []);
const kb = () => KB0.concat(custom);
function sourcesHtml(sources){
  if (!D.rag.length) return '';
  if (!sources.length) return `<div class="sect"><b>Company sources</b><span class="hint">Nothing in the indexed history mentions this.</span></div>`;
  return `<div class="sect"><b>Company sources (retrieved)</b><span class="hint">From fix commits, postmortems and learned bug patterns. Bob is told to cite these by number.</span></div>
    <ol class="srcs">${sources.map((s, i) => `<li><div class="row"><b>[${i + 1}]</b> <span>${esc(s.chunk.title)}</span></div>
      <div class="row"><span class="chip">${esc(s.chunk.kind)}</span><span class="hint mono">${esc(s.chunk.ref)}</span>
      <span class="hint">matched: ${esc(s.matched.join(', '))}</span></div>
      <div class="snip">${esc(s.chunk.text.replace(/\s+/g, ' ').slice(0, 220))}</div></li>`).join('')}</ol>`;
}

function bobPrompt(text, matches, sources = []){
  text = redactText(text)[0];
  const known = matches.filter(m => m.confidence === 'known bug').slice(0, 3);
  const ctx = known.map(m => `- ${m.a.title} (from ${m.a.repo}, fixed in: ${m.a.source_commit || '?'}). Pattern: ${m.a.pattern || ''}. Known fix: ${(m.a.signatures || {}).fix_hint || 'n/a'}`).join('\n')
    || '- No known company bug pattern matched. Treat this as a new bug.';
  const src = sources.length ? '\n## Retrieved company sources (cite them as [1], [2], ...)\n' + sources.map((s, i) =>
    `[${i + 1}] ${s.chunk.title} (${s.chunk.kind}, ${s.chunk.ref})\n${redactText(s.chunk.text)[0].slice(0, 900)}`).join('\n\n') + '\n' : '';
  return `You are debugging an issue at our company. Use our bug history first.

## The problem
\`\`\`
${text.trim().slice(0, 4000)}
\`\`\`

## Matching bugs we have already had (from Bug Vaccine's company knowledge base)
${ctx}
${src}
## What to do
0. Ground your answer in the sources above and cite them like [2]. If they don't cover the problem, say so plainly instead of guessing.
1. Check whether this is one of the known bugs above. If it is, point to the exact line and apply the known fix.
2. If it isn't, find the root cause yourself. Explain it in 2-3 sentences before changing anything.
3. Write a regression test that fails before the fix and passes after, and guard the *pattern*, not just this input.
4. If this is a new kind of bug, write a Bug Vaccine antigen for it (id, title, pattern, and a \`signatures\` block with
   \`code\` and \`errors\` regexes that work in both Python and JavaScript), so the company knowledge base learns it.
`;
}

/* ── debug UI ── */
const SAMPLES = [
  ['JavaScript crash', `TypeError: Cannot read properties of undefined (reading 'email')\n    at refundContact (src/refunds.js:8:27)\n    at processRefund (src/jobs/refunds.js:41:15)`],
  ['Customer report', `Ticket #4412: customer says their monthly invoice total is off by a cent. The PDF shows 0.30000000000000004 for two items.`],
  ['Python traceback', `Traceback (most recent call last):\n  File "app/config.py", line 14, in load_settings\n    return tomli.loads(raw)\n  File "tomli/_parser.py", line 623, in parse_hex_char\n    return pos, chr(hex_int)\nValueError: chr() arg not in range(0x110000)`],
  ['New code to review', `export function statementPage(entries, pageNo, perPage) {\n  const from = pageNo * perPage;\n  return entries.slice(from, from + perPage - 1);\n}\n\nexport function statementTotal(entries) {\n  return entries.reduce((sum, e) => sum + e.amount, 0);\n}\n\nexport function greeting(customer) {\n  return \`Hello \${customer.profile.firstName}\`;\n}`],
  ['Something new', `The login button does nothing on Safari 17 after the last release.`],
];
if (D.samples && D.samples.diff) SAMPLES.splice(4, 0, ['Pull request diff', D.samples.diff]);

function runDiff(text){
  const {files, findings} = matchDiff(text);
  $('#dbg-lang').textContent = `· pull request diff, ${Object.keys(files).length} file${Object.keys(files).length === 1 ? '' : 's'}, only added lines checked`;
  const hits = new Set(findings.map(f => f.file + ':' + f.line));
  $('#dbg-code').innerHTML = Object.entries(files).map(([f, added]) => `<div class="codeview" style="margin-bottom:8px"><span class="difffile">${esc(f)}</span>
    ${added.length ? added.map(([ln, l]) => `<div class="${hits.has(f + ':' + ln) ? 'hit' : ''}"><span class="ln">${ln}</span><span class="src">+ ${esc(l)}</span></div>`).join('')
      : '<div><span class="ln"></span><span class="src hint">no added lines</span></div>'}</div>`).join('');
  $('#dbg-code').hidden = false;
  const byBug = {};
  findings.forEach(f => (byBug[f.a.key] ||= {a: f.a, items: []}).items.push(f));
  const groups = Object.values(byBug);
  const head = groups.length
    ? `<div class="eyebrow">Pull request review</div><h2 class="bad">This diff repeats ${groups.length} bug${groups.length > 1 ? 's' : ''} your company has already fixed</h2>`
    : `<div class="eyebrow">Pull request review</div><h2 class="good">No known company bug in the lines this diff adds</h2><p class="lede">Only known patterns are checked. For a deeper review, hand the diff to Bob below.</p>`;
  const cards = groups.map(({a, items}) => { const s = a.signatures || {};
    return `<div class="match known"><div class="row"><span class="pill no">known bug</span><span class="chip">${esc(a.repo)}</span>${recurBadge(a)}</div>
      <h3>${esc(a.title)}</h3>
      <div class="reasons">${items.map(f => `<div><span class="k">${esc(f.file.split('/').pop())}:${f.line}</span><span><code>${esc(f.text)}</code><br><span class="hint">${esc(f.explain)}</span></span></div>`).join('')}</div>
      ${s.fix_hint ? `<div class="sect"><b>How it was fixed before</b>${esc(s.fix_hint)}</div>` : ''}${exampleDiff(s.example)}
      ${s.antibody ? `<div class="sect"><b>Test to add</b>${esc(s.antibody)}</div>` : ''}</div>`; }).join('');
  const pseudo = groups.map(g => ({a: g.a, confidence: 'known bug', score: 3 * g.items.length}));
  const query = findings.map(f => `${f.a.title} ${f.text}`).join('\n') || Object.values(files).flat().map(x => x[1]).join('\n');
  const sources = ragSearch(query, 4, pseudo);
  $('#dbg-out').innerHTML = `${head}${cards}${sourcesHtml(sources)}${promptHtml(text, pseudo, sources, "Paste this into IBM Bob, opened on the pull request's branch.")}`;
  bindPrompt(text, pseudo, sources);
}
function promptHtml(text, matches, sources, intro){
  const hidden = redactText(text)[1];
  return `<div class="sect"><b>Hand it to Bob</b>${esc(intro)}${hidden ? ` <span class="pill warn">${hidden} secret${hidden > 1 ? 's' : ''} redacted from the prompt</span>` : ''}</div>
    <pre class="prompt">${esc(bobPrompt(text, matches, sources))}</pre>
    <div class="row"><button class="btn primary" type="button" id="copy-prompt">Copy Bob prompt</button></div>`;
}
function bindPrompt(text, matches, sources){ $('#copy-prompt').onclick = () => copy(bobPrompt(text, matches, sources), 'Bob prompt copied'); }

/* drop a file (log, stack trace, source, .diff) into the box */
(() => { const ta = $('#dbg-input');
  ta.addEventListener('dragover', e => { e.preventDefault(); ta.classList.add('drag'); });
  ta.addEventListener('dragleave', () => ta.classList.remove('drag'));
  ta.addEventListener('drop', e => { e.preventDefault(); ta.classList.remove('drag');
    const f = e.dataTransfer.files && e.dataTransfer.files[0]; if (!f) return;
    if (f.size > 2e6) return toast('That file is over 2 MB. Paste the relevant part instead.');
    const r = new FileReader(); r.onload = () => { ta.value = r.result; runDebug(); toast('Loaded ' + f.name); }; r.readAsText(f); });
})();

function renderSamples(){
  $('#samples').innerHTML = SAMPLES.map(([l], i) => `<button type="button" data-i="${i}">${esc(l)}</button>`).join('');
  $('#samples').querySelectorAll('button').forEach(b => b.onclick = () => { $('#dbg-input').value = SAMPLES[+b.dataset.i][1]; runDebug(); });
}
function exampleDiff(ex){
  if (!ex) return '';
  return `<div class="diff">${ex.before.split('\n').map(l => `<div class="d">- ${esc(l)}</div>`).join('')}${ex.after.split('\n').map(l => `<div class="a">+ ${esc(l)}</div>`).join('')}</div>`;
}
function runDebug(){
  const text = $('#dbg-input').value;
  if (isDiff(text)) { runDiff(text); testTeach(); return; }
  const lang = detectLang(text);
  $('#dbg-lang').textContent = text.trim() ? (lang ? `· looks like ${lang}` : '· plain text') : '';
  const out = $('#dbg-out');
  if (!text.trim()) {
    out.innerHTML = `<div class="empty">Paste something on the left, or pick an example.</div>`; $('#dbg-code').hidden = true; return;
  }
  const matches = matchText(text);
  const hitLines = new Set(matches.flatMap(m => m.reasons.filter(r => r.kind === 'code').map(r => r.line)));
  if (hitLines.size) {
    $('#dbg-code').innerHTML = `<div class="codeview" aria-label="Your code with flagged lines">${text.split(/\r?\n/).map((l, i) =>
      `<div class="${hitLines.has(i + 1) ? 'hit' : ''}"><span class="ln">${i + 1}</span><span class="src">${esc(l) || ' '}</span></div>`).join('')}</div>`;
    $('#dbg-code').hidden = false;
  } else $('#dbg-code').hidden = true;

  const known = matches.filter(m => m.confidence === 'known bug');
  const head = known.length
    ? `<div class="eyebrow">Result</div><h2 class="bad">Your company has had this bug before${known.length > 1 ? ` (${known.length} matches)` : ''}</h2>`
    : `<div class="eyebrow">Result</div><h2>No known company bug matches</h2><p class="lede">This looks new. Hand it to Bob with the prompt below. When it's fixed, teach the pattern here so it's recognised next time.</p>`;
  const cards = matches.map(m => { const s = m.a.signatures || {};
    return `<div class="match ${m.confidence === 'known bug' ? 'known' : 'maybe'}">
      <div class="row"><span class="pill ${m.confidence === 'known bug' ? 'no' : 'warn'}">${m.confidence}</span><span class="chip">${esc(m.a.repo)}</span>${recurBadge(m.a)}
        ${m.a.custom ? '<span class="chip">added here</span>' : ''}</div>
      <h3>${esc(m.a.title)}</h3>
      <div class="reasons">${m.reasons.map(r => `<div><span class="k">${r.kind === 'code' ? 'line ' + r.line : r.kind === 'error' ? 'matched' : 'related'}</span>
        <span>${r.kind === 'keywords' ? 'shares the words: ' + esc(r.text) : `<code>${esc(r.text)}</code>`}${r.explain ? `<br><span class="hint">${esc(r.explain)}</span>` : ''}</span></div>`).join('')}</div>
      ${s.fix_hint ? `<div class="sect"><b>How it was fixed before</b>${esc(s.fix_hint)}</div>` : ''}
      ${exampleDiff(s.example)}
      ${s.antibody ? `<div class="sect"><b>Test to add</b>${esc(s.antibody)}</div>` : ''}
      ${m.a.source_commit || m.a.postmortem ? `<div class="sect"><b>History</b>${m.a.source_commit ? 'Fixed in ' + esc(m.a.source_commit) : ''}${m.a.postmortem ? ` · incident <code>${esc(m.a.postmortem)}</code>` : ''}</div>` : ''}
    </div>`; }).join('');
  const sources = ragSearch(text, 4, matches);
  out.innerHTML = `${head}${cards}${sourcesHtml(sources)}${promptHtml(text, matches, sources,
    'Paste this into IBM Bob, opened in the affected repo. It includes what your company already knows, with sources to cite.')}`;
  bindPrompt(text, matches, sources);
  testTeach();
}
let debTimer;
$('#dbg-input').addEventListener('input', () => { clearTimeout(debTimer); debTimer = setTimeout(runDebug, 180); });

/* ── teach ── */
function draftPattern(){
  const v = id => $(id).value.trim();
  const a = {id:'C' + (custom.length + 1), key:'custom:C' + (custom.length + 1), repo:'added here', custom:true, title:v('#t-title'), pattern:v('#t-pattern'),
    signatures:{lang:v('#t-lang'), code:v('#t-code') ? [{regex:v('#t-code'), explain:v('#t-pattern') || v('#t-title')}] : [], errors:v('#t-error') ? [v('#t-error')] : [], fix_hint:v('#t-fix')}};
  const bad = [...a.signatures.code.map(c => c.regex), ...a.signatures.errors].filter(p => !rx(p, 'im'));
  return {a, bad, risky: bad.filter(riskyRegex)};
}
function testTeach(){
  const {a, bad, risky} = draftPattern(), msg = $('#t-msg');
  if (!a.title && !a.signatures.code.length && !a.signatures.errors.length) { msg.textContent = ''; return; }
  if (risky.length) { msg.innerHTML = `<span class="bad">This regex could freeze on some inputs (a repeated group that itself repeats, like <code>(a+)+</code>). Rewrite it: <code>${esc(risky[0])}</code></span>`; return; }
  if (bad.length) { msg.innerHTML = `<span class="bad">This regex doesn't compile: <code>${esc(bad[0])}</code></span>`; return; }
  const text = $('#dbg-input').value, lines = text.split(/\r?\n/);
  const hits = a.signatures.errors.filter(p => rx(p, 'im').test(text)).length +
    a.signatures.code.reduce((n, c) => n + lines.filter(l => rx(c.regex, '').test(l)).length, 0);
  msg.innerHTML = text.trim() ? (hits ? `<span class="good">Matches the text on the left (${hits} hit${hits > 1 ? 's' : ''}).</span>` : `<span class="warn">Doesn't match the text on the left yet.</span>`) : '';
}
['#t-title', '#t-pattern', '#t-code', '#t-error', '#t-lang', '#t-fix'].forEach(id => $(id).addEventListener('input', testTeach));
$('#t-add').onclick = () => {
  const {a, bad} = draftPattern();
  if (!a.title) { $('#t-msg').innerHTML = '<span class="bad">Give the bug a name first.</span>'; return; }
  if (!a.signatures.code.length && !a.signatures.errors.length) { $('#t-msg').innerHTML = '<span class="bad">Add a code or error regex so it can be recognised.</span>'; return; }
  if (bad.length) return testTeach();
  custom.push(a); store.set('bv-custom', custom);
  ['#t-title', '#t-pattern', '#t-code', '#t-error', '#t-fix'].forEach(id => $(id).value = '');
  $('#t-msg').innerHTML = `<span class="good">Added "${esc(a.title)}". It's now part of this browser's knowledge.</span>`;
  renderKb(); runDebug();
};
$('#t-copy').onclick = () => {
  const {a} = draftPattern();
  const list = (a.title ? [a] : []).concat(custom).map(({key, repo, custom, ...rest}) => rest);
  if (!list.length) return toast('Nothing to copy yet');
  copy(JSON.stringify(list, null, 2), `${list.length} pattern${list.length > 1 ? 's' : ''} copied as JSON`);
};

/* ── knowledge table ── */
function renderKb(){
  const all = kb();
  $('#kb-count').textContent = `${all.length} known bug patterns`;
  const sources = D.knowledge ? D.knowledge.sources.map(s => `${s.name}: ${s.antigens}`).join(' · ') : 'no knowledge base loaded';
  $('#kb-sources').textContent = sources + (custom.length ? ` · added here: ${custom.length}` : '');
  if (!all.length) {
    $('#kb-table').innerHTML = `<div class="empty">Nothing learned yet. Build a knowledge base with <code>python bugvaccine.py learn &lt;repo&gt;</code>, then regenerate this dashboard with <code>--kb</code>.</div>`;
    return;
  }
  $('#kb-table').innerHTML = `<table class="kb"><thead><tr><th>Bug pattern</th><th>Repo</th><th>Recognises</th><th>Language</th><th></th></tr></thead><tbody>
    ${all.map((a, i) => { const s = a.signatures || {};
      return `<tr><td><b>${esc(a.title)}</b> ${recurBadge(a)}<div class="hint">${esc(a.pattern || '')}</div></td><td><span class="chip">${esc(a.repo)}</span></td>
        <td>${s.code || s.errors ? `${(s.code || []).length} code · ${(s.errors || []).length} error` : '<span class="hint">not taught yet</span>'}</td>
        <td>${esc(s.lang || 'any')}</td>
        <td>${a.custom ? `<button class="icon-btn" type="button" data-del="${esc(a.key)}">Remove</button>` : ''}</td></tr>`; }).join('')}
  </tbody></table>`;
  $('#kb-table').querySelectorAll('[data-del]').forEach(b => b.onclick = () => {
    custom = custom.filter(c => c.key !== b.dataset.del); store.set('bv-custom', custom); renderKb(); runDebug(); renderCompany(); });
}

/* ── company view ── */
const latest = p => p.after || p.before;
const survivors = r => r ? r.results.filter(x => x.status === 'survived').length : 0;
const secs = r => r ? r.results.reduce((t, x) => t + (x.seconds || 0), 0) : 0;
const fmt = v => Math.round(v).toLocaleString();
function renderCompany(){
  const P = D.projects.filter(p => p.before);
  const learned = name => kb().filter(a => a.repo === name).length;
  $('#projects').innerHTML = P.length ? `<table class="kb"><thead><tr><th>Project</th><th>Bug patterns</th><th>Past bugs caught</th><th></th><th>Could return</th></tr></thead><tbody>
    ${P.map(p => { const r = latest(p), s = survivors(r);
      return `<tr><td><b>${esc(p.name)}</b></td><td>${learned(p.name) || '—'}</td>
        <td style="font-variant-numeric:tabular-nums;white-space:nowrap">${p.after ? `<span class="bad">${p.before.immunity}%</span> → ` : ''}<b class="${r.immunity >= 90 ? 'good' : 'bad'}">${r.immunity}%</b> <span class="hint">${r.killed}/${r.total}</span></td>
        <td><div class="bar" aria-hidden="true"><i style="width:${r.immunity}%"></i></div></td>
        <td>${s ? `<span class="pill no">${s} unguarded</span>` : '<span class="pill ok">none</span>'}</td></tr>`; }).join('')}
    </tbody></table>` : '<div class="empty">No project results yet.</div>';
  const rec = kb().filter(a => recurCount(a) > 1);
  $('#recurring').innerHTML = rec.length ? rec.map(a => `<div class="match maybe"><div class="row">${recurBadge(a)}<span class="chip">${esc(a.repo)}</span></div>
      <h3>${esc(a.title)}</h3><div class="hint">${esc(a.pattern || '')} · commits ${esc(a.source_commit || '')}</div></div>`).join('')
    : '<p class="hint">No bug pattern has been fixed more than once yet.</p>';
  renderImpact();
}
function renderImpact(){
  const P = D.projects.filter(p => p.before);
  const num = id => Math.max(0, parseFloat($(id).value) || 0);
  const hours = num('#i-hours'), rate = num('#i-rate'), chance = Math.min(100, num('#i-chance')) / 100;
  store.set('bv-impact', [hours, rate, chance * 100]);
  const before = P.reduce((t, p) => t + survivors(p.before), 0), now = P.reduce((t, p) => t + survivors(latest(p)), 0);
  const cost = k => k * chance * hours * rate, hrs = k => k * chance * hours;
  const box = (label, big, note) => `<div class="readout"><span class="label">${label}</span><div class="big">${big}</div><span class="note">${note}</span></div>`;
  $('#impact').innerHTML =
    box('Unguarded past bugs', `<span class="bad">${before}</span><span class="arrow">→</span><span class="${now ? 'bad' : 'good'}">${now}</span>`, 'measured by re-injecting them') +
    box('Expected regression cost / year', `<span class="bad">${fmt(cost(before))}</span><span class="arrow">→</span><span class="good">${fmt(cost(now))}</span>`, 'in your currency') +
    box('Estimated saving / year', `<span class="good">${fmt(cost(before) - cost(now))}</span>`, `about ${fmt(hrs(before) - hrs(now))} engineer hours`) +
    box('Test time per full check', `${Math.max(1, Math.round(P.reduce((t, p) => t + secs(latest(p)), 0)))}<small>seconds</small>`, 'measured, all projects together');
  $('#impact-note').textContent = `How this is worked out: unguarded bugs × chance one returns in a year (${fmt(chance * 100)}%) × engineer hours per regression (${hours}) × cost per hour (${rate}). `
    + `Only the number of unguarded bugs and the test time are measured; everything else is your own assumption. A regression that reaches customers usually costs more than engineer time.`;
}
(() => { const saved = store.get('bv-impact', null);
  if (saved) ['#i-hours', '#i-rate', '#i-chance'].forEach((id, i) => $(id).value = saved[i]);
  ['#i-hours', '#i-rate', '#i-chance'].forEach(id => $(id).addEventListener('input', renderImpact)); })();

/* ── boot ── */
applyTheme();
$('#repo').textContent = D.meta.repo + ' · ' + D.meta.generated;
renderSummary();
renderSamples();
renderKb();
renderCompany();
$('#dbg-input').value = SAMPLES[3][1];
runDebug();
const mm = /^#step-(\d)$/.exec(location.hash);
cur = mm ? +mm[1] - 1 : 0;
showView(['#debug', '#company'].includes(location.hash) ? location.hash.slice(1) : 'vaccine');
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
