/* Bug Vaccine matching engine: the browser twin of vaccine/debug.py, rag.py and redact.py.
 * Pure functions only (no DOM), so the same file runs in the dashboard and under Node, where
 * tests/test_js_parity.py checks it gives exactly the same answers as the Python modules.
 * The dashboard inlines this file; its rules (redaction, ReDoS check, RAG settings) come from
 * the Python modules through `config`, so the two can't drift apart.
 */
(function (root) {
  'use strict';
  function create({ getKb, rag = [], config = {} }) {
    const CFG = config;
    const num = v => Number.isFinite(+v) ? +v : 0;

    const REDACT = (CFG.redact || []).map(([name, src, flags, how]) => { try { return [name, new RegExp(src, 'g' + flags), how]; } catch (e) { return null; } }).filter(Boolean);
    function redactText(t){
      let n = 0;
      for (const [name, re, how] of REDACT) t = t.replace(re, (...m) => { n++;
        return how === 'value' ? m[1] + (name === 'url-credentials' ? '[REDACTED]' : `[REDACTED:${name}]`) : `[REDACTED:${name}]`; });
      return [t, n];
    }
    const NESTED = (() => { try { return new RegExp(CFG.nestedQuantifier || '(?!)'); } catch (e) { return /(?!)/; } })();
    const riskyRegex = p => NESTED.test(p);
    const MAX_TEXT = num(CFG.maxText) || 200000, MAX_LINE = num(CFG.maxLine) || 2000;

    const STOPW = new Set(`the and for with that this from into when then than have has was were are not but you your our
    their them they its it's any all can could would should will does did done been being also only just more most
    other some such each every very what which while where there here about after before over under again`.split(/\s+/));
    const reCache = {};
    function rx(src, flags){ const k = flags + '|' + src;
      if (!(k in reCache)) { try { reCache[k] = riskyRegex(src) ? null : new RegExp(src, flags); } catch (e) { reCache[k] = null; } }
      return reCache[k]; }
    function detectLang(t){
      if (/Traceback \(most recent call last\)|^\s*def \w+\(|^\s*import \w+$|\bself\./m.test(t)) return 'python';
      if (/=>|\bconst \w+|\bfunction\b|\bexport \w+|at \w+ \(.*\.[jt]s:\d+/.test(t)) return 'javascript';
      return null;
    }
    const wordsOf = t => new Set((t.toLowerCase().match(/[a-z][a-z0-9_]{3,}/g) || []).filter(w => !STOPW.has(w)));
    function matchText(text){
      text = text.slice(0, MAX_TEXT);
      const lang = detectLang(text), lines = text.split(/\r?\n/).map(l => l.slice(0, MAX_LINE)), tw = wordsOf(text), out = [];
      for (const a of getKb()) {
        const s = a.signatures || {}, reasons = []; let score = 0;
        for (const pat of s.errors || []) {
          const r = rx(pat, 'im'), m = r && r.exec(text);
          if (!m) continue;
          const snip = m[0].trim().split(/\r?\n/).pop().trim().slice(0, 160);
          if (!reasons.some(x => x.text === snip)) { score += 5; reasons.push({kind:'error', text:snip}); }
        }
        if (!lang || !s.lang || s.lang === lang)
          for (const c of s.code || []) { const r = rx(c.regex, ''); if (!r) continue;
            lines.forEach((line, i) => { if (r.test(line)) { score += 3; reasons.push({kind:'code', line:i + 1, text:line.trim().slice(0, 160), explain:c.explain}); } }); }
        const shared = [...wordsOf(`${a.title || ''} ${a.pattern || ''}`)].filter(w => tw.has(w));
        if (shared.length && (score || shared.length >= 2)) { score += Math.min(shared.length, 3); reasons.push({kind:'keywords', text:shared.sort().slice(0, 6).join(', ')}); }
        if (score) out.push({a, score, reasons, confidence: score >= 3 ? 'known bug' : 'possibly related'});
      }
      return out.sort((x, y) => y.score - x.score);
    }

    /* RAG: BM25 + signature boost (mirrors vaccine/rag.py hybrid_search) */
    const RC = CFG.rag || {}, RSTOP = new Set(RC.stop || []), K1 = num(RC.k1) || 1.2, BB = num(RC.b) || 0.75, BOOST = num(RC.boost) || 2;
    function rtokens(t){
      t = (t || '').replace(/([a-z0-9])([A-Z])/g, '$1 $2');
      const out = [];
      for (let w of (t.toLowerCase().match(/[a-z0-9]+/g) || [])) {
        if (w.length < 2 || RSTOP.has(w)) continue;
        if (w.length > 4 && w.endsWith('s') && !w.endsWith('ss')) w = w.slice(0, -1);
        out.push(w);
      }
      return out;
    }
    let RDOCS = null;
    function ragSearch(q, k, sigMatches){
      const chunks = rag; if (!chunks.length) return [];
      RDOCS ||= chunks.map(c => rtokens(`${c.title} ${c.title} ${c.text}`));
      const qs = [...new Set(rtokens(q.slice(0, MAX_TEXT)))], n = RDOCS.length;
      const avg = RDOCS.reduce((t, d) => t + d.length, 0) / n || 1, df = {};
      qs.forEach(t => df[t] = RDOCS.filter(d => d.includes(t)).length);
      const hits = new Map();
      chunks.forEach((c, i) => { const d = RDOCS[i]; let s = 0; const m = [];
        for (const t of qs) { const tf = d.filter(x => x === t).length; if (!tf) continue;
          s += Math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) * tf * (K1 + 1) / (tf + K1 * (1 - BB + BB * d.length / avg)); m.push(t); }
        if (s > 0) hits.set(c.id, {score: s, chunk: c, matched: m.sort()}); });
      for (const sm of sigMatches || []) {
        if (sm.confidence !== 'known bug') continue;
        const c = chunks.find(x => x.ref === sm.a.key); if (!c) continue;
        const h = hits.get(c.id) || {score: 0, chunk: c, matched: []};
        h.score += BOOST * sm.score; h.matched = [...new Set([...h.matched, 'signature'])].sort(); hits.set(c.id, h);
      }
      return [...hits.values()].sort((a, b) => b.score - a.score || a.chunk.id - b.chunk.id).slice(0, k);
    }

    /* diff review (mirrors debug.parse_diff / match_diff) */
    const EXT_LANG = {'.py':'python', '.js':'javascript', '.mjs':'javascript', '.cjs':'javascript', '.jsx':'javascript',
      '.ts':'javascript', '.tsx':'javascript', '.java':'java', '.go':'go'};
    const isDiff = t => /^(diff --git |@@ -\d+(,\d+)? \+\d+(,\d+)? @@)/m.test(t);
    function parseDiff(t){
      const files = {}; let file = null, ln = 0;
      for (const line of t.slice(0, MAX_TEXT).split(/\r?\n/)) {
        if (line.startsWith('+++ ')) { const p = line.slice(4).trim(); file = p === '/dev/null' ? null : p.replace(/^b\//, ''); if (file) files[file] ||= []; }
        else if (line.startsWith('@@')) { const m = /@@ -\d+(?:,\d+)? \+(\d+)/.exec(line); ln = m ? +m[1] : 0; }
        else if (file === null || line.startsWith('--- ') || line.startsWith('diff --git')) continue;
        else if (line.startsWith('+')) { files[file].push([ln, line.slice(1)]); ln++; }
        else if (!line.startsWith('-') && !line.startsWith('\\')) ln++;
      }
      return files;
    }
    function matchDiff(t){
      const out = [], files = parseDiff(t);
      for (const [path, added] of Object.entries(files)) {
        const lang = EXT_LANG[((path.match(/\.[^./]+$/) || [''])[0]).toLowerCase()];
        for (const a of getKb()) { const s = a.signatures || {};
          if (lang && s.lang && s.lang !== lang) continue;
          for (const c of s.code || []) { const r = rx(c.regex, ''); if (!r) continue;
            for (const [ln, line] of added) if (r.test(line.slice(0, MAX_LINE))) out.push({file:path, line:ln, text:line.trim().slice(0, 160), explain:c.explain, a}); } }
      }
      return {files, findings: out.sort((x, y) => (x.file < y.file ? -1 : x.file > y.file ? 1 : 0) || x.line - y.line)};
    }

    return { redactText, riskyRegex, rx, detectLang, matchText, rtokens, ragSearch, isDiff, parseDiff, matchDiff,
             MAX_TEXT, MAX_LINE };
  }
  const api = { create };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.BugVaccineEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
