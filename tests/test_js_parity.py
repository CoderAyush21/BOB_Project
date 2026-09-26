"""The dashboard's JavaScript engine (vaccine/web/engine.js) must give exactly the same answers as
the Python modules it mirrors. Runs the same inputs through both and compares.
Run:  python -m unittest discover tests      (needs Node.js; skipped without it)"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vaccine"))

import debug  # noqa: E402
import rag  # noqa: E402
import redact  # noqa: E402

KB = debug.learn([("invoice-kit", ROOT / "examples/mutants.example.json"),
                  ("tomli", ROOT / "case-studies/tomli/mutants.json")])
CHUNKS = rag.build_index(rag.chunks_from_antigens(ROOT / "examples/mutants.example.json", "invoice-kit")
                         + rag.chunks_from_antigens(ROOT / "case-studies/tomli/mutants.json", "tomli")
                         + rag.chunks_from_docs([ROOT / "docs/USING-ON-YOUR-REPO.md"]))["chunks"]
CONFIG = {"redact": [[n, p, f, h] for n, p, f, h in redact.RULES],
          "nestedQuantifier": debug._NESTED_QUANTIFIER.pattern,
          "maxText": debug.MAX_TEXT, "maxLine": debug.MAX_LINE,
          "rag": {"stop": sorted(rag.STOP), "k1": rag.K1, "b": rag.B, "boost": rag.SIGNATURE_BOOST}}

SAMPLES = {
    "js crash": "TypeError: Cannot read properties of undefined (reading 'email')\n    at refundContact (src/refunds.js:8:27)",
    "customer report": "Ticket #4412: invoice total is off by a cent, shows 0.30000000000000004 for two items.",
    "python traceback": (ROOT / "examples/debug-samples/python-traceback.txt").read_text(encoding="utf-8"),
    "new code": (ROOT / "examples/debug-samples/new-feature.js").read_text(encoding="utf-8"),
    "unknown": "The login button does nothing on Safari 17 after the last release.",
    # fake credentials, assembled at runtime so secret scanners don't flag this file
    "secrets": 'DB_PASSWORD="Sup3rS3cretValue"\nurl = postgres://admin:hunter2pass@db:5432/x\nkey ' + "AKIA" + "ABCDEFGHIJKLMNOP",
}
DIFF = (ROOT / "examples/debug-samples/pr-88.diff").read_text(encoding="utf-8")
RISKY = [r"(a+)+$", r"(\w+)*x", r"\.slice\([^)]*[+-]\s*1\s*\)", r"(abc)+"]

NODE_SCRIPT = r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const E = require(input.engine).create({getKb: () => input.kb, rag: input.chunks, config: input.config});
const out = {match: {}, rag: {}, redact: {}, diff: null, risky: {}};
for (const [name, text] of Object.entries(input.samples)) {
  const m = E.matchText(text);
  out.match[name] = m.map(x => ({key: x.a.key, score: x.score, confidence: x.confidence,
                                 reasons: x.reasons.map(r => [r.kind, r.line || null, r.text])}));
  out.rag[name] = E.ragSearch(text, 5, m).map(h => [h.chunk.id, Math.round(h.score * 1000) / 1000, h.matched]);
  out.redact[name] = E.redactText(text)[0];
}
out.diff = E.matchDiff(input.diff).findings.map(f => [f.file, f.line, f.a.key]);
for (const p of input.risky) out.risky[p] = E.riskyRegex(p);
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "needs Node.js")
class JsPythonParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = {"engine": str(ROOT / "vaccine/web/engine.js"), "kb": KB["antigens"], "chunks": CHUNKS,
                   "config": CONFIG, "samples": SAMPLES, "diff": DIFF, "risky": RISKY}
        r = subprocess.run(["node", "-e", NODE_SCRIPT], input=json.dumps(payload), capture_output=True,
                           text=True, encoding="utf-8")
        if r.returncode:
            raise AssertionError(r.stderr)
        cls.js = json.loads(r.stdout)

    def test_signature_matching_is_identical(self):
        for name, text in SAMPLES.items():
            with self.subTest(sample=name):
                py = [{"key": m["key"], "score": m["score"], "confidence": m["confidence"],
                       "reasons": [[r["kind"], r.get("line"), r["text"]] for r in m["reasons"]]}
                      for m in debug.match(text, KB)]
                self.assertEqual(self.js["match"][name], py)

    def test_rag_retrieval_is_identical(self):
        for name, text in SAMPLES.items():
            with self.subTest(sample=name):
                py = [[h["chunk"]["id"], round(h["score"], 3), h["matched"]]
                      for h in rag.hybrid_search(text, CHUNKS, KB, 5)]
                self.assertEqual(self.js["rag"][name], py)

    def test_redaction_is_identical(self):
        for name, text in SAMPLES.items():
            with self.subTest(sample=name):
                self.assertEqual(self.js["redact"][name], redact.redact_text(text))

    def test_diff_review_is_identical(self):
        py = [[f["file"], f["line"], f["key"]] for f in debug.match_diff(DIFF, KB)]
        self.assertEqual(self.js["diff"], py)
        self.assertTrue(py, "the sample diff should produce findings")

    def test_redos_check_is_identical(self):
        for p in RISKY:
            with self.subTest(pattern=p):
                self.assertEqual(self.js["risky"][p], debug.risky_regex(p))


if __name__ == "__main__":
    unittest.main()
