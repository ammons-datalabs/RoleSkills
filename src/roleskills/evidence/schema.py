"""
Evidence chunk schema and data models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvidenceChunk:
    """
    Represents a single piece of authored code evidence from version control.

    Attributes:
        evidence_id: Unique identifier (content hash)
        repo: Repository name
        owner: Repository owner/org
        commit: Git commit SHA
        author: Author handle
        path: File path relative to repo root
        start: Starting line number
        end: Ending line number
        text: The actual code/content
        lang: Programming language or None
        ownership: Ownership multiplier (0.7-1.3)
        recency: Recency score based on commit age (0-1)
        quality: Quality score from deterministic heuristics (0.5-1.2)
        anchor: Stable GitHub permalink
        created_at: Timestamp when indexed
    """

    evidence_id: str
    repo: str
    owner: str
    commit: str
    author: str
    path: str
    start: int
    end: int
    text: str
    lang: str | None
    ownership: float
    recency: float
    quality: float
    anchor: str
    created_at: datetime