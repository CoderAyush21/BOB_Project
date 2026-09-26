"""Redact secrets before text leaves the tool (dossiers, RAG index, dashboard, Bob prompts).

Git history often contains credentials that were committed and later removed.
Bug Vaccine reads that history, so everything it writes out goes through here.
The same rules run in the dashboard's JavaScript (keep them JS-compatible:
no inline flags; case-insensitivity is set per rule).
"""
import re

_SECRET_NAME = r"[\w.-]*(?:api[_-]?key|apikey|secret|password|passwd|pwd|token|access[_-]?key|credential)s?"

# (name, pattern, flags, how). how: "all" replaces the whole match; "value" keeps group 1 (and a
# closing quote, if any) and replaces only the secret value.
#   flags: "i" = case-insensitive, "m" = ^/$ match per line (same letters as JavaScript RegExp flags)
RULES = [
    ("private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", "", "all"),
    ("aws-access-key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "", "all"),
    ("github-token", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "", "all"),
    ("slack-token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b", "", "all"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "", "all"),
    ("url-credentials", r"(\b[a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s@/]{3,}(?=@)", "i", "value"),
    # quoted value:  API_KEY = "abc..."   password: 'abc...'
    ("assigned-secret", r"(\b" + _SECRET_NAME + r"[\"']?\s*[:=]\s*([\"']))[^\"'\s]{8,}(?=\2)", "i", "value"),
    # config-style line of its own (.env / YAML / INI):  API_KEY=abc...   password: abc...
    ("assigned-secret", r"^(\s*(?:export\s+)?" + _SECRET_NAME + r"\s*[:=]\s*)[^\s\"'()]{8,}\s*$", "im", "value"),
]
_FLAGS = {"i": re.I, "m": re.M}
_COMPILED = [(name, re.compile(p, sum(_FLAGS[f] for f in flags)), how) for name, p, flags, how in RULES]


def redact(text):
    """Return (redacted_text, {rule_name: count})."""
    if not text:
        return text, {}
    counts = {}
    for name, rx, how in _COMPILED:
        def sub(m, name=name, how=how):
            counts[name] = counts.get(name, 0) + 1
            if how == "value":
                label = "[REDACTED]" if name == "url-credentials" else f"[REDACTED:{name}]"
                return m.group(1) + label
            return f"[REDACTED:{name}]"
        text = rx.sub(sub, text)
    return text, counts


def redact_text(text):
    return redact(text)[0]
