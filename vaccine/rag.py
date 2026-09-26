"""RAG for company bug knowledge: index -> retrieve -> grounded prompt with citations.

Index (the "R" corpus), built from each repo:
  - fix commits: subject, body and the changed lines of the diff
  - incident docs / postmortems, split into sections
  - learned bug patterns (antigens): pattern, fix, test advice
  - any extra docs you add (runbooks, READMEs): --docs
Retrieval: BM25 with code-aware tokens (camelCase / snake_case split, light plural stemming).
Generation: IBM Bob (or any LLM) gets the top-k chunks as numbered sources and must cite them.

Why lexical BM25 and not embeddings: it needs no model download or API key, sends no code
anywhere, is deterministic and explainable (you can see which words matched), and the exact
same scoring runs in the offline dashboard. Every chunk is secret-redacted at index time.
"""
import datetime as dt
import json
import math
import re
from pathlib import Path

import mine
from redact import redact_text

K1, B = 1.2, 0.75
MAX_CHUNK = 1500
STOP = set("""the and for with that this from into when then than have has was were are not but you your our
their them they its any all can could would should will does did done been being also only just more most
other some such each every very what which while where there here about after before over under again why how
use used using get got let var const def return new true false none null
of to in on is it at by an be or as if do no so up we us me my""".split())
SIGNATURE_BOOST = 2.0


def tokens(text):
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")           # camelCase -> camel Case
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):                  # snake_case and punctuation split
        if len(w) < 2 or w in STOP:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


# ── building the corpus ────────────────────────────────────────────────────

def _changed_lines(diff):
    keep = [l for l in diff.splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    return "\n".join(keep)[:MAX_CHUNK]


def _sections(text):
    """Split a Markdown doc into (heading, body) sections."""
    parts, heading, buf = [], None, []
    for line in text.splitlines():
        if re.match(r"^#{1,3} ", line):
            if buf and "".join(buf).strip():
                parts.append((heading, "\n".join(buf).strip()))
            heading, buf = line.lstrip("# ").strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        parts.append((heading, "\n".join(buf).strip()))
    return parts


# Commits the fix-detector flags but that aren't behaviour bugs: they only add noise to retrieval.
# (The dossier Bob reads still includes them; only the RAG index skips them.)
NOT_A_BUG = re.compile(
    r"\b(ci|mypy|typing|type hints?|lint(ing|er)?|flake8|ruff|black|isort|format(ting)?|typo|badge|readme|docs?|"
    r"changelog|pre-commit|benchmark|bump|deps|dependabot|speed up|perf(ormance)?|github actions)\b", re.I)


def is_noise(subject):
    return bool(NOT_A_BUG.search(subject))


def chunks_from_repo(repo, name):
    out = []
    for sha, date, subject, body in mine.fix_commits(repo):
        if is_noise(subject):
            continue
        diff = mine.git(repo, "show", "--format=", "--unified=1", sha)
        out.append({"kind": "fix", "repo": name, "ref": f"{name}@{sha[:7]}", "title": subject,
                    "text": f"{subject}\n{body}\n{_changed_lines(diff)}".strip()})
    for path in mine.incident_docs(repo):
        text = (Path(repo) / path).read_text(encoding="utf-8", errors="replace")
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), path)
        for heading, body in _sections(text):
            out.append({"kind": "postmortem", "repo": name, "ref": path,
                        "title": f"{title} > {heading}" if heading and heading != title else title,
                        "text": body[:MAX_CHUNK]})
    return out


def chunks_from_antigens(path, name):
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for a in spec["antigens"] if isinstance(spec, dict) else spec:
        s = a.get("signatures", {})
        text = "\n".join(filter(None, [
            a.get("title"), a.get("pattern"), s.get("fix_hint"), s.get("antibody"),
            *[c.get("explain", "") for c in s.get("code", [])], a.get("source_commit"),
            *a.get("unfinished_followups", [])]))
        out.append({"kind": "pattern", "repo": name, "ref": f"{name}:{a['id']}", "title": a.get("title", a["id"]),
                    "text": text[:MAX_CHUNK]})
    return out


def chunks_from_docs(paths, name="docs"):
    out = []
    for p in paths:
        text = Path(p).read_text(encoding="utf-8", errors="replace")
        for heading, body in _sections(text):
            out.append({"kind": "doc", "repo": name, "ref": Path(p).name,
                        "title": heading or Path(p).name, "text": body[:MAX_CHUNK]})
    return out


def build_index(chunks):
    # The same bug pattern can arrive twice (a repo's own antigens and a --source file): keep the first.
    seen, unique = set(), []
    for c in chunks:
        key = (c["kind"], c["ref"]) if c["kind"] == "pattern" else None
        if key and key in seen:
            continue
        seen.add(key)
        unique.append(c)
    chunks = unique
    for i, c in enumerate(chunks, 1):
        c["id"] = i
        c["title"] = redact_text(c["title"])
        c["text"] = redact_text(c["text"])
    return {"version": 1, "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "retriever": "bm25", "chunks": chunks}


# ── retrieval ──────────────────────────────────────────────────────────────

def search(query, chunks, k=5):
    """BM25 over title+text. Returns [{"score", "chunk", "matched": [terms]}], best first."""
    q = set(tokens(query))
    if not q or not chunks:
        return []
    docs = [tokens(f"{c['title']} {c['title']} {c['text']}") for c in chunks]  # title counted twice
    n = len(docs)
    avgdl = sum(map(len, docs)) / n or 1
    df = {t: sum(1 for d in docs if t in d) for t in q}
    results = []
    for c, d in zip(chunks, docs):
        score, matched = 0.0, []
        for t in q:
            tf = d.count(t)
            if not tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * len(d) / avgdl))
            matched.append(t)
        if score > 0:
            results.append({"score": round(score, 3), "chunk": c, "matched": sorted(matched)})
    results.sort(key=lambda r: (-r["score"], r["chunk"]["id"]))
    return results[:k]


def hybrid_search(query, chunks, kb=None, k=5):
    """BM25 plus the debugger's signature matcher: a bug pattern whose code/error signature matches the
    query gets a boost, so '0.30000000000000004' finds the float-money pattern even with no shared words."""
    hits = {h["chunk"]["id"]: h for h in search(query, chunks, k=len(chunks))}
    if kb:
        import debug
        by_ref = {c["ref"]: c for c in chunks}
        for m in debug.match(query, kb):
            c = by_ref.get(m["key"])
            if not c or m["confidence"] != "known bug":
                continue
            h = hits.setdefault(c["id"], {"score": 0.0, "chunk": c, "matched": []})
            h["score"] = round(h["score"] + SIGNATURE_BOOST * m["score"], 3)
            h["matched"] = sorted(set(h["matched"]) | {"signature"})
    return sorted(hits.values(), key=lambda h: (-h["score"], h["chunk"]["id"]))[:k]


def grounded_prompt(question, hits):
    """A RAG prompt: numbered sources + instructions to answer only from them, with citations."""
    q = redact_text(question).strip()[:4000]
    if not hits:
        src = "(no company sources matched this question)"
    else:
        src = "\n\n".join(f"[{i}] {h['chunk']['title']}  ({h['chunk']['kind']}, {h['chunk']['ref']})\n{h['chunk']['text']}"
                          for i, h in enumerate(hits, 1))
    return f"""Answer using our company's own bug history. The sources below were retrieved from it.

## Question
{q}

## Sources
{src}

## Rules
- Use only these sources for company-specific facts, and cite them like [1] or [2][3] after each claim.
- If the sources don't answer the question, say "Our history doesn't cover this" and then give your best general advice, clearly marked as general.
- If a source describes the same bug, say so first, point to its fix, and name the regression test that guards it.
- Never repeat anything that looks like a credential, even if it appears in a source.
"""
