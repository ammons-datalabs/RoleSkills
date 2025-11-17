"""Lexical retrieval using SQLite FTS5."""

from __future__ import annotations

from typing import List, Tuple

from ..evidence.store import EvidenceStore
from .query import Query


def build_fts_query(query: Query, use_and: bool = False) -> str:
    """
    Build FTS5 query string from Query object.

    Args:
        query: Search query
        use_and: If True, AND terms together; else OR

    Returns:
        FTS5 query string

    Example:
        >>> from .query import Query
        >>> q = Query(requirement_id="1", terms=["azure", "functions"], tags=["azure"], weight=3.0)
        >>> build_fts_query(q, use_and=False)
        'azure OR functions'
        >>> build_fts_query(q, use_and=True)
        'azure AND functions'
    """
    # Combine tags (higher priority) and terms
    all_terms = list(query.tags) + [t for t in query.terms if t not in query.tags]

    if not all_terms:
        return "*"

    # Normalize terms for FTS5: replace hyphens with spaces
    # (FTS5 treats hyphens as operators, not part of words)
    normalized_terms = [term.replace("-", " ") for term in all_terms]

    # Build query
    operator = " AND " if use_and else " OR "
    fts_query = operator.join(normalized_terms)

    return fts_query


def lexical_search(
    store: EvidenceStore,
    query: Query,
    max_candidates: int = 200,
    use_and: bool = False,
) -> List[Tuple[str, float]]:
    """
    Perform lexical search using FTS5.

    Args:
        store: Evidence store
        query: Search query
        max_candidates: Maximum results to return
        use_and: If True, AND terms together; else OR

    Returns:
        List of (evidence_id, bm25_score) tuples, sorted by relevance

    Example:
        >>> from roleskills.evidence import EvidenceStore
        >>> from .query import Query
        >>> store = EvidenceStore(":memory:")
        >>> q = Query(requirement_id="1", terms=["python"], tags=["python"], weight=3.0)
        >>> results = lexical_search(store, q, max_candidates=10)
        >>> len(results) <= 10
        True
    """
    fts_query = build_fts_query(query, use_and=use_and)

    # Query FTS5 table
    # BM25 scores are negative (lower is better), so we negate for sorting
    sql = """
        SELECT e.evidence_id, -bm25(evidence_fts) as score
        FROM evidence_fts
        JOIN evidence e ON e.rowid = evidence_fts.rowid
        WHERE evidence_fts MATCH ?
        ORDER BY score DESC
        LIMIT ?
    """

    try:
        results = store.conn.execute(sql, (fts_query, max_candidates)).fetchall()
        return [(row[0], row[1]) for row in results]
    except Exception:
        # If FTS query fails (malformed, etc.), return empty
        return []