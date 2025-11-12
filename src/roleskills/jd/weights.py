"""Weight inference for requirements."""

from __future__ import annotations

import re

from .schema import Weight

# Order matters: first match wins
_MUST = [
    r"\bmust(-|\s)?have\b",
    r"\brequired\b",
    r"\bwe\s+require\b",
    r"\bminimum\b",
    r"\bat\s+least\b",
    r"\byou\s+will\b",
]
_STRONG = [
    r"\bstrong\b",
    r"\bproven\b|\bdemonstrated\b|\bsolid\b",
    r"\bexpert(ise)?\b",
    r"\b[xX]\s*\+\s*years\b",  # "X+ years" → strong by default
]
_NICE = [
    r"\bnice\s*to\s*have\b",
    r"\bpreferred\b|\bpreference\b",
    r"\bbonus\b|\bplus\b",
    r"\bfamiliar(ity)?\b",
    r"\bdesirable\b|\bbeneficial\b",
]

_MUST_R = [re.compile(p, re.I) for p in _MUST]
_STRONG_R = [re.compile(p, re.I) for p in _STRONG]
_NICE_R = [re.compile(p, re.I) for p in _NICE]


def infer_weight(line: str) -> Weight:
    """Infer requirement weight from text cues."""
    s = line.strip()
    for rx in _NICE_R:
        if rx.search(s):
            nice_hit = True
            break
    else:
        nice_hit = False

    for rx in _MUST_R:
        if rx.search(s):
            return Weight.must
    for rx in _STRONG_R:
        if rx.search(s):
            return Weight.strong
    if nice_hit:
        return Weight.nice
    # default: treat unlabelled requirements as strong
    return Weight.strong