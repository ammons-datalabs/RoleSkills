"""Deterministic JD parser (no LLM)."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable, List, Tuple

from .schema import JD, Requirement, Weight
from .tags import detect_tags
from .weights import infer_weight

# Headings likely to contain requirements
_REQ_HEADINGS = [
    r"requirements?",
    r"what\s+you['\s]*ll\s+bring",
    r"what\s+we['\s]*re\s+looking\s+for",
    r"skills",
    r"qualifications?",
    r"about\s+you",
    r"key\s+selection\s+criteria",
    r"this\s+role\s+will",
    r"to\s+be\s+successful",
    r"you\s+will\s+be\s+able\s+to\s+demonstrate",
]
# Headings to ignore
_IGNORE_HEADINGS = [
    r"benefits?",
    r"about\s+the\s+company|about\s+us",
    r"perks?|compensation|salary|pay|why\s+us",
    r"visa|work\s+rights|eeo|diversity",
    r"how\s+to\s+apply|application\s+process",
]

_REQ_H = re.compile(rf"^\s{{0,3}}(?:#+\s+)?(?P<h>{'|'.join(_REQ_HEADINGS)})\b.*$", re.I | re.M)
_IGN_H = re.compile(rf"^\s{{0,3}}(?:#+\s+)?(?P<h>{'|'.join(_IGNORE_HEADINGS)})\b.*$", re.I | re.M)

_BULLET = re.compile(r"^\s*(?:[-*•]|\d+\.)\s+(?P<txt>.+)$")


def _section_spans(md: str) -> List[Tuple[str, int, int]]:
    """Return (section_name, start_idx, end_idx). Minimal, robust to plain text."""
    lines = md.splitlines()
    spans: List[Tuple[str, int, int]] = []
    current = ("__top__", 0)
    for i, ln in enumerate(lines):
        if _IGN_H.search(ln):
            # close current and start an ignored block with sentinel
            if current[0] != "__top__":
                spans.append((current[0], current[1], i))
            current = ("__ignore__", i)
        elif _REQ_H.search(ln):
            if current[0] != "__top__":
                spans.append((current[0], current[1], i))
            sec = _REQ_H.search(ln).group("h").lower()  # type: ignore
            current = (sec, i)
    spans.append((current[0], current[1], len(lines)))
    return spans


def _iter_requirement_lines(section_text: str) -> Iterable[str]:
    """Extract requirement lines from section text."""
    # Prefer bullets; if none, fall back to sentences.
    out: List[str] = []
    for ln in section_text.splitlines():
        m = _BULLET.match(ln)
        if m:
            out.append(m.group("txt").strip())
    if out:
        return out
    # Split by semicolon/period if no bullets present
    chunk = " ".join(section_text.split())
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z0-9])", chunk)
    return [p.strip() for p in parts if len(p.strip()) >= 12]


def _normalize_title(text: str) -> str:
    """Normalize requirement title by stripping prefixes and punctuation."""
    # Strip trailing punctuation and leading weight/requirement cues
    t = re.sub(
        r"^\b(must have|required|we require|nice to have|preferred|strong|proven|solid|demonstrated|bonus|plus):?\s*",
        "",
        text,
        flags=re.I,
    )
    t = re.sub(r"\s*\(.*?\)\s*$", "", t)  # drop trailing parentheses
    t = t.strip(" .;:-")
    # Capitalize first letter
    if t:
        t = t[0].upper() + t[1:]
    return t


def _mk_id(text: str) -> str:
    """Generate deterministic ID from text."""
    return hashlib.sha1(text.strip().lower().encode("utf-8")).hexdigest()[:12]


def parse_jd(md: str, role: str | None = None, title: str | None = None) -> JD:
    """Parse job description markdown into structured JD."""
    lines = md.splitlines()
    spans = _section_spans(md)
    reqs: List[Requirement] = []

    for name, a, b in spans:
        if name == "__ignore__":
            continue
        if name in ("__top__",):
            continue  # we only parse explicit requirement-like sections
        sec_text = "\n".join(lines[a + 1 : b])  # skip heading line itself
        for raw in _iter_requirement_lines(sec_text):
            if len(raw) < 6:
                continue
            w = infer_weight(raw)
            title_norm = _normalize_title(raw)
            if not title_norm:
                continue
            tags = sorted(detect_tags(raw))
            rid = _mk_id(f"{name}|{title_norm}")
            reqs.append(
                Requirement(
                    id=rid,
                    title=title_norm,
                    weight=w,
                    tags=tags,
                    source_text=raw,
                    section=name,
                )
            )

    # Dedup identical titles within same section (keep strongest weight)
    by_key = {}
    order: List[Tuple[str | None, str]] = []
    for r in reqs:
        k = (r.section, r.title.lower())
        if k not in by_key:
            by_key[k] = r
            order.append(k)
        else:
            # Keep higher weight (must > strong > nice)
            prev = by_key[k]
            if prev.weight in (Weight.nice, Weight.strong) and r.weight == Weight.must:
                by_key[k] = r
            elif prev.weight == Weight.nice and r.weight == Weight.strong:
                by_key[k] = r
            else:
                # merge tags
                merged = sorted(set(prev.tags) | set(r.tags))
                prev.tags = merged
                by_key[k] = prev
    out = [by_key[k] for k in order]
    return JD(role=role, title=title, requirements=out)