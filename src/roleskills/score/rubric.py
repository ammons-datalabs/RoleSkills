"""Deterministic scoring rubric."""

from __future__ import annotations

from typing import List

from ..jd.schema import JD, Requirement, WEIGHT_NUM
from .factors import Factor
from .models import RequirementScore


def score_requirement(req: Requirement, factor: Factor) -> float:
    """
    Score a single requirement using multi-factor rubric.

    Formula:
        score = weight × coverage × relevance × ownership × recency × quality

    Args:
        req: JD requirement
        factor: Computed factors

    Returns:
        Score (0.0 - weight×1.5 typically)

    Example:
        >>> from roleskills.jd.schema import Requirement, Weight
        >>> req = Requirement(id="1", title="Python", weight=Weight.must, tags=["python"], source_text="")
        >>> f = Factor(coverage=1.0, relevance=0.9, ownership=1.2, recency=0.8, quality=1.1)
        >>> score_requirement(req, f)
        2.851...
    """
    weight = WEIGHT_NUM[req.weight]

    # Multiplicative scoring
    base = (
        factor.coverage
        * factor.relevance
        * factor.ownership
        * factor.recency
        * factor.quality
    )

    # Weight and clamp
    score = weight * max(0.0, min(base, 1.5))

    return round(score, 3)


def overall_match(jd: JD, requirement_scores: List[RequirementScore]) -> float:
    """
    Compute overall match score across all requirements.

    Formula:
        overall = Σ(score_i) / Σ(weight_i)

    Args:
        jd: Job description
        requirement_scores: List of scored requirements

    Returns:
        Overall match score (0.0-1.0)

    Example:
        >>> from roleskills.jd.schema import JD, Requirement, Weight
        >>> jd = JD(requirements=[
        ...     Requirement(id="1", title="Python", weight=Weight.must, tags=[], source_text=""),
        ...     Requirement(id="2", title="Azure", weight=Weight.strong, tags=[], source_text=""),
        ... ])
        >>> scores = [
        ...     RequirementScore(id="1", title="Python", weight="must", score=2.7, coverage=1.0, relevance=0.9, ownership=1.0, recency=1.0, quality=1.0),
        ...     RequirementScore(id="2", title="Azure", weight="strong", score=1.6, coverage=1.0, relevance=0.8, ownership=1.0, recency=1.0, quality=1.0),
        ... ]
        >>> overall_match(jd, scores)
        0.86
    """
    if not jd.requirements:
        return 0.0

    # Build lookup
    score_map = {rs.id: rs.score for rs in requirement_scores}

    # Weighted average
    total_score = 0.0
    total_weight = 0.0

    for req in jd.requirements:
        w = WEIGHT_NUM[req.weight]
        s = score_map.get(req.id, 0.0)
        total_score += s
        total_weight += w

    if total_weight == 0:
        return 0.0

    return round(total_score / total_weight, 3)