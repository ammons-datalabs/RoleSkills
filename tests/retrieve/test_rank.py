"""Tests for evidence ranking."""

from datetime import datetime, timezone

from roleskills.evidence.schema import EvidenceChunk
from roleskills.retrieve.query import Query
from roleskills.retrieve.rank import (
    infer_tags_from_evidence,
    compute_tag_score,
    compute_path_score,
    normalize_lexical_score,
    rerank_evidence,
)


def test_infer_tags_basic():
    """Test tag inference from text and path."""
    text = "import azure.functions as func and python code"
    path = "src/api/handler.py"

    tags = infer_tags_from_evidence(text, path)

    assert "azure" in tags
    assert "functions" in tags
    assert "python" in tags  # From text


def test_infer_tags_from_path():
    """Test tag inference from path only."""
    text = "some github actions code"
    path = ".github/workflows/test.yml"

    tags = infer_tags_from_evidence(text, path)

    assert "github-actions" in tags


def test_compute_tag_score_full_overlap():
    """Test tag scoring with full overlap."""
    query_tags = ["azure", "functions"]
    evidence_tags = {"azure", "functions", "python"}

    score = compute_tag_score(query_tags, evidence_tags)

    assert score == 1.0


def test_compute_tag_score_no_overlap():
    """Test tag scoring with no overlap."""
    query_tags = ["azure", "functions"]
    evidence_tags = {"python", "django"}

    score = compute_tag_score(query_tags, evidence_tags)

    assert score == 0.5  # Minimum score


def test_compute_tag_score_empty_query():
    """Test tag scoring with no query tags."""
    query_tags = []
    evidence_tags = {"python"}

    score = compute_tag_score(query_tags, evidence_tags)

    assert score == 0.8  # Neutral


def test_compute_path_score_tests():
    """Test path scoring for test files."""
    query = Query(requirement_id="1", terms=["test"], tags=[], weight=2.0)

    # Test file with "test" in query
    score = compute_path_score("tests/test_api.py", query)
    assert score == 1.0

    # Test file without "test" in query
    query_no_test = Query(requirement_id="1", terms=["api"], tags=[], weight=2.0)
    score = compute_path_score("tests/test_api.py", query_no_test)
    assert score == 0.9


def test_compute_path_score_docs():
    """Test path scoring for documentation."""
    query = Query(requirement_id="1", terms=["azure"], tags=[], weight=2.0)

    score = compute_path_score("docs/README.md", query)
    assert score == 0.6


def test_compute_path_score_source():
    """Test path scoring for source code."""
    query = Query(requirement_id="1", terms=["api"], tags=[], weight=2.0)

    score = compute_path_score("src/api/handler.py", query)
    assert score == 1.0


def test_normalize_lexical_score_top_rank():
    """Test lexical score normalization for top result."""
    score = normalize_lexical_score(bm25_score=10.0, rank=0, max_score=10.0)

    assert score == 1.0


def test_normalize_lexical_score_with_decay():
    """Test lexical score normalization with rank decay."""
    score = normalize_lexical_score(bm25_score=10.0, rank=10, max_score=10.0)

    # Should be less than 1.0 due to rank penalty
    assert 0.5 <= score < 1.0


def test_rerank_evidence_basic():
    """Test evidence reranking."""
    query = Query(
        requirement_id="req1", terms=["azure", "functions"], tags=["azure"], weight=3.0
    )

    chunks = [
        EvidenceChunk(
            evidence_id="e1",
            repo="test-repo",
            owner="testowner",
            commit="abc123",
            author="testuser",
            path="src/azure_handler.py",
            start=1,
            end=20,
            text="import azure.functions as func",
            lang="python",
            ownership=1.2,
            recency=0.9,
            quality=1.1,
            anchor="https://github.com/...",
            created_at=datetime.now(timezone.utc),
        ),
        EvidenceChunk(
            evidence_id="e2",
            repo="test-repo",
            owner="testowner",
            commit="def456",
            author="testuser",
            path="docs/README.md",
            start=1,
            end=10,
            text="Azure documentation",
            lang="markdown",
            ownership=1.0,
            recency=0.5,
            quality=0.8,
            anchor="https://github.com/...",
            created_at=datetime.now(timezone.utc),
        ),
    ]

    lexical_scores = [10.0, 8.0]

    hits = rerank_evidence(query, chunks, lexical_scores, max_evidence=5)

    assert len(hits) == 2

    # First hit should be the source code (higher combined relevance)
    assert hits[0].evidence_id == "e1"
    assert hits[0].combined_relevance > hits[1].combined_relevance

    # Check scores are populated
    assert 0.5 <= hits[0].score_lexical <= 1.0
    assert 0.5 <= hits[0].score_tags <= 1.0
    assert 0.5 <= hits[0].score_path <= 1.0


def test_rerank_evidence_max_limit():
    """Test max evidence limit."""
    query = Query(requirement_id="req1", terms=["test"], tags=[], weight=2.0)

    chunks = [
        EvidenceChunk(
            evidence_id=f"e{i}",
            repo="test-repo",
            owner="testowner",
            commit="abc",
            author="testuser",
            path=f"src/file{i}.py",
            start=1,
            end=10,
            text=f"code {i}",
            lang="python",
            ownership=1.0,
            recency=0.5,
            quality=1.0,
            anchor="https://github.com/...",
            created_at=datetime.now(timezone.utc),
        )
        for i in range(10)
    ]

    lexical_scores = [10.0 - i * 0.5 for i in range(10)]

    hits = rerank_evidence(query, chunks, lexical_scores, max_evidence=3)

    assert len(hits) == 3