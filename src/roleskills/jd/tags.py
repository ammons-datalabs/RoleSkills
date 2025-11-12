"""Tag detection for skill recognition in JDs."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Set

# Canonical tag → list of regex patterns (case-insensitive)
_SKILL_LEXICON: Dict[str, Iterable[str]] = {
    # languages
    "python": [r"\bpython\b"],
    "csharp": [r"\b(c#|csharp)\b"],
    "java": [r"\bjava(?!script)\b"],
    "javascript": [r"\b(java\s*script|javascript|js)\b"],
    "typescript": [r"\btypescript\b"],
    # frameworks / libs
    "fastapi": [r"\bfastapi\b"],
    "flask": [r"\bflask\b"],
    "django": [r"\bdjango\b"],
    "pytest": [r"\bpytest\b"],
    "pandas": [r"\bpandas\b"],
    "numpy": [r"\bnumpy\b"],
    # cloud
    "azure": [r"\bazure\b"],
    "aws": [r"\baws\b", r"\bamazon web services\b"],
    "gcp": [r"\bgcp\b", r"\bgoogle cloud\b"],
    # integration
    "apim": [r"\bapi management\b|\bapim\b"],
    "service-bus": [r"\bservice\s*bus\b"],
    "logic-apps": [r"\blogic\s*apps?\b"],
    "event-grid": [r"\bevent\s*grid\b"],
    "event-hub": [r"\bevent\s*hubs?\b"],
    # platform / tooling
    "git": [r"\bgit\b"],
    "github-actions": [r"\bgithub actions\b"],
    "docker": [r"\bdocker\b"],
    "mypy": [r"\bmypy\b"],
    "ruff": [r"\bruff\b"],
    # data / db
    "sql": [r"\bsql\b"],
    "postgres": [r"\bpostgres(?:ql)?\b"],
    "sqlite": [r"\bsqlite\b"],
    # testing / quality
    "tdd": [r"\btdd\b|\btest[-\s]*driven\b"],
    "coverage": [r"\bcoverage\b|\bcode coverage\b"],
}

_COMPILED = {k: [re.compile(p, re.I) for p in pats] for k, pats in _SKILL_LEXICON.items()}


def detect_tags(text: str) -> Set[str]:
    """Detect skill tags in text using lexicon patterns."""
    hits: Set[str] = set()
    for tag, patterns in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            hits.add(tag)
    return hits