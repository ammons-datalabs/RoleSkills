"""Tests for factor computation."""


from roleskills.score.factors import compute_factors
from roleskills.score.models import EvidenceHit


def test_compute_factors_with_hits():
    """Test factor computation with evidence hits."""
    hits = [
        EvidenceHit(
            evidence_id="e1",
            repo="test-repo",
            owner="testuser",
            path="src/api.py",
            anchor="https://github.com/...",
            text_snippet="import azure",
            score_lexical=0.9,
            score_tags=0.8,
            score_path=1.0,
            combined_relevance=0.85,
            ownership=1.2,
            recency=0.9,
            quality=1.1,
        ),
        EvidenceHit(
            evidence_id="e2",
            repo="test-repo",
            owner="testuser",
            path="tests/test_api.py",
            anchor="https://github.com/...",
            text_snippet="def test_azure():",
            score_lexical=0.8,
            score_tags=0.7,
            score_path=0.9,
            combined_relevance=0.75,
            ownership=1.0,
            recency=0.8,
            quality=1.0,
        ),
    ]

    factors = compute_factors(hits, min_relevance_for_coverage=0.6)

    # Should use best hit (e1)
    assert factors.coverage == 1.0  # 0.85 >= 0.6
    assert factors.relevance == 0.85
    assert factors.ownership == 1.2
    assert factors.recency == 0.9
    assert factors.quality == 1.1


def test_compute_factors_below_threshold():
    """Test coverage=0 when relevance below threshold."""
    hits = [
        EvidenceHit(
            evidence_id="e1",
            repo="test-repo",
            owner="testuser",
            path="docs/README.md",
            anchor="https://github.com/...",
            text_snippet="# Documentation",
            score_lexical=0.6,
            score_tags=0.5,
            score_path=0.6,
            combined_relevance=0.55,  # Below default 0.6 threshold
            ownership=1.0,
            recency=0.5,
            quality=0.8,
        ),
    ]

    factors = compute_factors(hits)

    assert factors.coverage == 0.0  # 0.55 < 0.6
    assert factors.relevance == 0.55


def test_compute_factors_empty_hits():
    """Test factor defaults with no evidence."""
    factors = compute_factors([])

    assert factors.coverage == 0.0
    assert factors.relevance == 0.5
    assert factors.ownership == 0.3
    assert factors.recency == 0.0
    assert factors.quality == 0.5


def test_compute_factors_custom_threshold():
    """Test custom relevance threshold."""
    hits = [
        EvidenceHit(
            evidence_id="e1",
            repo="test-repo",
            owner="testuser",
            path="src/api.py",
            anchor="https://github.com/...",
            text_snippet="code",
            score_lexical=0.7,
            score_tags=0.7,
            score_path=1.0,
            combined_relevance=0.7,
            ownership=1.0,
            recency=0.8,
            quality=1.0,
        ),
    ]

    # With higher threshold, no coverage
    factors = compute_factors(hits, min_relevance_for_coverage=0.8)
    assert factors.coverage == 0.0

    # With lower threshold, has coverage
    factors = compute_factors(hits, min_relevance_for_coverage=0.5)
    assert factors.coverage == 1.0