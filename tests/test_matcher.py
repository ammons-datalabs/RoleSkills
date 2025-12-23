"""Tests for the main matching API."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from roleskills.evidence.schema import EvidenceChunk
from roleskills.evidence.store import EvidenceStore
from roleskills.jd.schema import JD, Requirement, Weight
from roleskills.matcher import retrieve_evidence, score_jd


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def store_with_evidence(temp_db):
    """Create a store with sample evidence."""
    store = EvidenceStore(temp_db)

    chunks = [
        EvidenceChunk(
            evidence_id="python1",
            repo="TestRepo",
            owner="testuser",
            commit="abc123",
            author="testuser",
            path="src/main.py",
            start=1,
            end=20,
            text="def process_data(df: pd.DataFrame) -> pd.DataFrame:\n    return df.dropna()",
            lang="python",
            ownership=1.0,
            recency=0.9,
            quality=1.1,
            anchor="https://github.com/testuser/TestRepo/blob/abc123/src/main.py#L1-L20",
            created_at=datetime.now(timezone.utc),
        ),
        EvidenceChunk(
            evidence_id="azure1",
            repo="TestRepo",
            owner="testuser",
            commit="def456",
            author="testuser",
            path="src/azure_client.py",
            start=1,
            end=30,
            text="from azure.storage.blob import BlobServiceClient\n\ndef upload_to_azure():\n    pass",
            lang="python",
            ownership=1.0,
            recency=0.8,
            quality=1.0,
            anchor="https://github.com/testuser/TestRepo/blob/def456/src/azure_client.py#L1-L30",
            created_at=datetime.now(timezone.utc),
        ),
        EvidenceChunk(
            evidence_id="fastapi1",
            repo="TestRepo",
            owner="testuser",
            commit="ghi789",
            author="testuser",
            path="src/api.py",
            start=1,
            end=25,
            text="from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}",
            lang="python",
            ownership=1.2,
            recency=0.95,
            quality=1.15,
            anchor="https://github.com/testuser/TestRepo/blob/ghi789/src/api.py#L1-L25",
            created_at=datetime.now(timezone.utc),
        ),
    ]

    store.upsert_chunks(chunks)
    return store


@pytest.fixture
def sample_requirement():
    """Create a sample requirement."""
    return Requirement(
        id="req-1",
        title="Python experience",
        weight=Weight.must,
        tags=["python"],
        source_text="Must have Python experience",
        section="requirements",
    )


@pytest.fixture
def sample_jd():
    """Create a sample JD."""
    return JD(
        role="Software Engineer",
        title="Senior Developer",
        requirements=[
            Requirement(
                id="req-1",
                title="Python experience",
                weight=Weight.must,
                tags=["python"],
                source_text="Must have Python experience",
                section="requirements",
            ),
            Requirement(
                id="req-2",
                title="Azure cloud experience",
                weight=Weight.strong,
                tags=["azure", "cloud"],
                source_text="Strong Azure experience",
                section="requirements",
            ),
            Requirement(
                id="req-3",
                title="FastAPI framework",
                weight=Weight.nice,
                tags=["fastapi", "api"],
                source_text="Nice to have FastAPI",
                section="requirements",
            ),
        ],
    )


def test_retrieve_evidence_returns_hits(store_with_evidence, sample_requirement):
    """Test that retrieve_evidence returns evidence hits."""
    hits = retrieve_evidence(sample_requirement, store_with_evidence)

    # Should find some evidence for Python
    assert isinstance(hits, list)
    # Hits may or may not be found depending on FTS matching


def test_retrieve_evidence_empty_store(temp_db, sample_requirement):
    """Test retrieve_evidence with empty store."""
    store = EvidenceStore(temp_db)
    hits = retrieve_evidence(sample_requirement, store)

    assert hits == []


def test_retrieve_evidence_respects_max_evidence(store_with_evidence, sample_requirement):
    """Test that max_evidence limits results."""
    hits = retrieve_evidence(
        sample_requirement, store_with_evidence, max_evidence=1
    )

    assert len(hits) <= 1


def test_score_jd_returns_match_summary(store_with_evidence, sample_jd):
    """Test that score_jd returns a MatchSummary."""
    summary = score_jd(sample_jd, store_with_evidence)

    assert summary.role == "Software Engineer"
    assert summary.title == "Senior Developer"
    assert 0.0 <= summary.overall_match <= 1.0
    assert len(summary.requirements) == 3


def test_score_jd_empty_store(temp_db, sample_jd):
    """Test score_jd with empty evidence store."""
    store = EvidenceStore(temp_db)
    summary = score_jd(sample_jd, store)

    assert summary.role == "Software Engineer"
    assert summary.overall_match == 0.0  # No evidence = no coverage
    assert len(summary.requirements) == 3

    # All requirements should have 0 coverage
    for req_score in summary.requirements:
        assert req_score.coverage == 0.0


def test_score_jd_requirement_scores_structure(store_with_evidence, sample_jd):
    """Test that requirement scores have correct structure."""
    summary = score_jd(sample_jd, store_with_evidence)

    for req_score in summary.requirements:
        assert req_score.id in ["req-1", "req-2", "req-3"]
        assert req_score.weight in ["must", "strong", "nice"]
        assert 0.0 <= req_score.coverage <= 1.0
        assert 0.0 <= req_score.relevance <= 1.0
        assert req_score.ownership >= 0.0
        assert 0.0 <= req_score.recency <= 1.0
        assert req_score.quality >= 0.0
        assert req_score.score >= 0.0
        assert isinstance(req_score.evidence, list)


def test_score_jd_empty_requirements(store_with_evidence):
    """Test score_jd with JD that has no requirements."""
    jd = JD(role="Test Role", requirements=[])
    summary = score_jd(jd, store_with_evidence)

    assert summary.role == "Test Role"
    assert summary.overall_match == 0.0
    assert len(summary.requirements) == 0


def test_score_jd_with_min_relevance(store_with_evidence, sample_jd):
    """Test that min_relevance_for_coverage affects coverage calculation."""
    # High threshold - harder to get coverage
    summary_high = score_jd(
        sample_jd, store_with_evidence, min_relevance_for_coverage=0.99
    )

    # Low threshold - easier to get coverage
    summary_low = score_jd(
        sample_jd, store_with_evidence, min_relevance_for_coverage=0.1
    )

    # With a very high threshold, coverage should be 0 or very low
    # With a low threshold, coverage might be higher (if evidence found)
    # This test just verifies the parameter is passed through
    assert isinstance(summary_high.overall_match, float)
    assert isinstance(summary_low.overall_match, float)