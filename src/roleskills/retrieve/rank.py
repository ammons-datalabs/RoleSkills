"""Heuristic reranking of evidence."""

from __future__ import annotations

import re
from typing import List, Set

from ..evidence.schema import EvidenceChunk
from ..score.models import EvidenceHit
from .query import Query


def infer_tags_from_evidence(text: str, path: str) -> Set[str]:
    """
    Infer skill tags from evidence text and path.

    Args:
        text: Evidence text
        path: File path

    Returns:
        Set of detected tags

    Example:
        >>> infer_tags_from_evidence("import azure.functions", "src/api/handler.py")
        {'azure', 'functions'}
    """
    tags = set()
    combined = f"{text} {path}".lower()

    # Common patterns (extend from jd/tags.py lexicon)
    patterns = {
        "python": r"\bpython\b",
        "azure": r"\bazure\b",
        "functions": r"\bfunctions\b",
        "fastapi": r"\bfastapi\b",
        "pytest": r"\bpytest\b",
        "docker": r"\bdocker\b",
        "git": r"\bgit\b",
        "sql": r"\bsql\b",
        "pandas": r"\bpandas\b",
        "numpy": r"\bnumpy\b",
        "ray": r"\bray\b",
        "redis": r"\bredis\b",
        "logic-apps": r"\blogic[-\s]?apps?\b",
        "service-bus": r"\bservice[-\s]?bus\b",
        "apim": r"\bapi[-\s]?management\b|\bapim\b",
        "event-hub": r"\bevent[-\s]?hubs?\b",
        "github-actions": r"\bgithub[-\s]?actions\b",
    }

    for tag, pattern in patterns.items():
        if re.search(pattern, combined, re.IGNORECASE):
            tags.add(tag)

    return tags


def compute_tag_score(query_tags: List[str], evidence_tags: Set[str]) -> float:
    """
    Compute tag overlap score.

    Args:
        query_tags: Required tags from JD
        evidence_tags: Detected tags in evidence

    Returns:
        Score in range [0.5, 1.0]

    Example:
        >>> compute_tag_score(["azure", "functions"], {"azure", "functions", "python"})
        1.0
        >>> compute_tag_score(["azure", "functions"], {"python"})
        0.5
    """
    if not query_tags:
        return 0.8  # Neutral if no specific tags

    overlap = len(set(query_tags) & evidence_tags)
    max_overlap = min(len(query_tags), 3)  # Cap at 3 for diminishing returns

    # Linear interpolation: 0 overlap → 0.5, full overlap → 1.0
    score = 0.5 + 0.5 * (overlap / max_overlap)

    return min(1.0, score)


def compute_path_score(path: str, query: Query) -> float:
    """
    Compute path relevance score.

    Args:
        path: File path
        query: Search query

    Returns:
        Score in range [0.6, 1.0]

    Example:
        >>> from .query import Query
        >>> q = Query(requirement_id="1", terms=["test"], tags=[], weight=2.0)
        >>> compute_path_score("tests/test_api.py", q)
        1.0
        >>> compute_path_score("docs/README.md", q)
        0.6
    """
    path_lower = path.lower()

    # Tests: high relevance if "test" in query, medium otherwise
    if path_lower.startswith("tests/") or "/test_" in path_lower:
        if "test" in query.terms or "pytest" in query.tags:
            return 1.0
        else:
            return 0.9  # Still valuable

    # Documentation: lower relevance
    if (
        "/docs/" in path_lower
        or path_lower.endswith(".md")
        or path_lower.endswith(".mmd")
        or path_lower.endswith(".rst")
    ):
        return 0.6

    # CI/CD: medium-high relevance
    if ".github/workflows" in path_lower or "azure-pipelines" in path_lower:
        return 0.9

    # Source code: high relevance
    if path_lower.startswith("src/") or path_lower.endswith((".py", ".ts", ".js")):
        return 1.0

    # Default
    return 0.8


def normalize_lexical_score(
    bm25_score: float, rank: int, max_score: float
) -> float:
    """
    Normalize BM25 score to [0.5, 1.0] range.

    Args:
        bm25_score: Raw BM25 score (higher is better after negation)
        rank: Position in results (0-indexed)
        max_score: Maximum BM25 score in result set

    Returns:
        Normalized score

    Example:
        >>> normalize_lexical_score(10.0, 0, 10.0)
        1.0
        >>> normalize_lexical_score(5.0, 5, 10.0)
        0.75
    """
    if max_score <= 0:
        return 0.5

    # Normalize by max score
    score_norm = bm25_score / max_score

    # Penalize by rank (exponential decay)
    rank_penalty = 0.95**rank

    # Combine and scale to [0.5, 1.0]
    final = 0.5 + 0.5 * score_norm * rank_penalty

    return min(1.0, max(0.5, final))


def rerank_evidence(
    query: Query,
    candidates: List[EvidenceChunk],
    lexical_scores: List[float],
    max_evidence: int = 5,
) -> List[EvidenceHit]:
    """
    Rerank evidence candidates using heuristic scoring.

    Args:
        query: Search query
        candidates: Evidence chunks from lexical search
        lexical_scores: BM25 scores for each candidate
        max_evidence: Maximum results to return

    Returns:
        List of EvidenceHit objects, sorted by combined_relevance

    Example:
        >>> from roleskills.evidence.schema import EvidenceChunk
        >>> from .query import Query
        >>> from datetime import datetime, timezone
        >>> q = Query(requirement_id="1", terms=["azure"], tags=["azure"], weight=3.0)
        >>> chunks = [EvidenceChunk(
        ...     evidence_id="e1",
        ...     repo="test-repo",
        ...     owner="testowner",
        ...     commit="abc123",
        ...     author="testuser",
        ...     path="src/api.py",
        ...     start=1,
        ...     end=10,
        ...     text="import azure.functions",
        ...     ownership=1.0,
        ...     recency=0.9,
        ...     quality=1.1,
        ...     anchor="https://github.com/...",
        ...     created_at=datetime.now(timezone.utc)
        ... )]
        >>> hits = rerank_evidence(q, chunks, [10.0], max_evidence=5)
        >>> len(hits)
        1
        >>> hits[0].combined_relevance > 0.5
        True
    """
    if not candidates:
        return []

    # Find max lexical score for normalization
    max_lex_score = max(lexical_scores) if lexical_scores else 1.0

    hits = []

    for rank, (chunk, lex_score) in enumerate(zip(candidates, lexical_scores)):
        # Normalize lexical score
        score_lexical = normalize_lexical_score(lex_score, rank, max_lex_score)

        # Compute tag overlap
        evidence_tags = infer_tags_from_evidence(chunk.text, chunk.path)
        score_tags = compute_tag_score(query.tags, evidence_tags)

        # Compute path relevance
        score_path = compute_path_score(chunk.path, query)

        # Combined relevance (weighted average)
        combined_relevance = (
            0.5 * score_lexical + 0.3 * score_tags + 0.2 * score_path
        )

        # Create hit
        hit = EvidenceHit(
            evidence_id=chunk.evidence_id,
            repo=chunk.repo,
            owner=chunk.owner,
            path=chunk.path,
            anchor=chunk.anchor,
            text_snippet=chunk.text[:200],  # First 200 chars
            score_lexical=round(score_lexical, 3),
            score_tags=round(score_tags, 3),
            score_path=round(score_path, 3),
            combined_relevance=round(combined_relevance, 3),
            ownership=chunk.ownership,
            recency=chunk.recency,
            quality=chunk.quality,
        )

        hits.append(hit)

    # Sort by combined relevance (descending)
    hits.sort(key=lambda h: h.combined_relevance, reverse=True)

    # Return top N
    return hits[:max_evidence]