"""Data models for scoring."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceHit(BaseModel):
    """A single evidence chunk matched to a requirement."""

    evidence_id: str
    repo: str
    owner: str
    path: str
    anchor: str
    text_snippet: str = Field(default="")

    # Retrieval scores
    score_lexical: float = Field(ge=0.0, le=1.0)
    score_tags: float = Field(ge=0.0, le=1.0)
    score_path: float = Field(ge=0.0, le=1.0)
    combined_relevance: float = Field(ge=0.0, le=1.0)

    # Evidence metadata
    ownership: float = Field(ge=0.0, le=2.0)
    recency: float = Field(ge=0.0, le=1.0)
    quality: float = Field(ge=0.0, le=1.5)


class RequirementScore(BaseModel):
    """Score for a single JD requirement."""

    id: str
    title: str
    weight: str  # "must", "strong", "nice"

    # Scoring factors
    coverage: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    ownership: float = Field(ge=0.0, le=2.0)
    recency: float = Field(ge=0.0, le=1.0)
    quality: float = Field(ge=0.0, le=1.5)

    # Final score
    score: float = Field(ge=0.0)

    # Supporting evidence
    evidence: List[EvidenceHit] = Field(default_factory=list)


class MatchSummary(BaseModel):
    """Overall match summary for a JD."""

    role: Optional[str] = None
    title: Optional[str] = None
    overall_match: float = Field(ge=0.0, le=1.0)
    requirements: List[RequirementScore] = Field(default_factory=list)