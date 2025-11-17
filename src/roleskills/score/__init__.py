"""Scoring layer - match JD requirements to evidence."""

from .factors import Factor, compute_factors
from .models import EvidenceHit, RequirementScore, MatchSummary
from .rubric import score_requirement, overall_match

__all__ = [
    "Factor",
    "compute_factors",
    "EvidenceHit",
    "RequirementScore",
    "MatchSummary",
    "score_requirement",
    "overall_match",
]