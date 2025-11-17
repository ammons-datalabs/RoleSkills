"""Main matching API - orchestrates retrieval and scoring."""

from __future__ import annotations

from typing import List

from .evidence.schema import EvidenceChunk
from .evidence.store import EvidenceStore
from .jd.schema import JD, Requirement
from .retrieve import requirement_to_query, lexical_search, rerank_evidence
from .score import (
    compute_factors,
    score_requirement,
    overall_match,
    RequirementScore,
    MatchSummary,
    EvidenceHit,
)


def retrieve_evidence(
    req: Requirement,
    store: EvidenceStore,
    max_candidates: int = 200,
    max_evidence: int = 5,
) -> List[EvidenceHit]:
    """
    Retrieve evidence for a single requirement.

    Args:
        req: JD requirement
        store: Evidence store
        max_candidates: Max candidates from lexical search
        max_evidence: Max evidence to return

    Returns:
        List of EvidenceHit objects
    """
    # Convert requirement to query
    query = requirement_to_query(req)

    # Lexical search
    lexical_results = lexical_search(
        store, query, max_candidates=max_candidates, use_and=False
    )

    if not lexical_results:
        return []

    # Fetch evidence chunks
    evidence_ids = [eid for eid, _ in lexical_results]
    chunks = store.get_chunks_by_ids(evidence_ids)

    # Create chunk lookup
    chunk_map = {c.evidence_id: c for c in chunks}

    # Align chunks with scores
    candidates: List[EvidenceChunk] = []
    scores: List[float] = []

    for eid, score in lexical_results:
        if eid in chunk_map:
            candidates.append(chunk_map[eid])
            scores.append(score)

    # Rerank
    hits = rerank_evidence(query, candidates, scores, max_evidence=max_evidence)

    return hits


def score_jd(
    jd: JD,
    store: EvidenceStore,
    max_candidates: int = 200,
    max_evidence: int = 5,
    min_relevance_for_coverage: float = 0.6,
) -> MatchSummary:
    """
    Score a JD against evidence index.

    Args:
        jd: Job description
        store: Evidence store
        max_candidates: Max candidates per requirement from lexical search
        max_evidence: Max evidence per requirement to return
        min_relevance_for_coverage: Minimum relevance to count as coverage

    Returns:
        MatchSummary with scores and evidence

    Example:
        >>> from roleskills.jd.schema import JD, Requirement, Weight
        >>> from roleskills.evidence import EvidenceStore
        >>> jd = JD(requirements=[
        ...     Requirement(id="1", title="Python", weight=Weight.must, tags=["python"], source_text="")
        ... ])
        >>> store = EvidenceStore(":memory:")
        >>> summary = score_jd(jd, store)
        >>> summary.role is None
        True
    """
    requirement_scores: List[RequirementScore] = []

    for req in jd.requirements:
        # Retrieve evidence
        hits = retrieve_evidence(
            req, store, max_candidates=max_candidates, max_evidence=max_evidence
        )

        # Compute factors
        factors = compute_factors(hits, min_relevance_for_coverage)

        # Score requirement
        score = score_requirement(req, factors)

        # Build result
        req_score = RequirementScore(
            id=req.id,
            title=req.title,
            weight=req.weight.value,
            coverage=factors.coverage,
            relevance=factors.relevance,
            ownership=factors.ownership,
            recency=factors.recency,
            quality=factors.quality,
            score=score,
            evidence=hits,
        )

        requirement_scores.append(req_score)

    # Compute overall match
    overall = overall_match(jd, requirement_scores)

    return MatchSummary(
        role=jd.role,
        title=jd.title,
        overall_match=overall,
        requirements=requirement_scores,
    )