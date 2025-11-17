"""Factor computation for scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import EvidenceHit


@dataclass
class Factor:
    """Scoring factors for a requirement."""

    coverage: float  # 0 or 1 (binary: is there evidence?)
    relevance: float  # 0.0-1.0 (how relevant is the evidence?)
    ownership: float  # 0.0-2.0 (ownership multiplier)
    recency: float  # 0.0-1.0 (exponential decay)
    quality: float  # 0.0-1.5 (code quality score)


def compute_factors(
    hits: List[EvidenceHit],
    min_relevance_for_coverage: float = 0.6,
) -> Factor:
    """
    Compute scoring factors from evidence hits.

    Args:
        hits: List of evidence hits for a requirement
        min_relevance_for_coverage: Minimum relevance to count as coverage

    Returns:
        Factor struct with computed values

    Example:
        >>> hits = [EvidenceHit(combined_relevance=0.85, ownership=1.2, ...)]
        >>> f = compute_factors(hits)
        >>> f.coverage
        1.0
        >>> f.relevance
        0.85
    """
    if not hits:
        return Factor(
            coverage=0.0,
            relevance=0.5,
            ownership=0.3,
            recency=0.0,
            quality=0.5,
        )

    # Find best hit by combined relevance
    best = max(hits, key=lambda h: h.combined_relevance)

    # Coverage: binary based on threshold
    coverage = 1.0 if best.combined_relevance >= min_relevance_for_coverage else 0.0

    return Factor(
        coverage=coverage,
        relevance=best.combined_relevance,
        ownership=best.ownership,
        recency=best.recency,
        quality=best.quality,
    )