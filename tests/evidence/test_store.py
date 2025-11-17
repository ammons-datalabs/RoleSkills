"""Tests for evidence storage."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from roleskills.evidence.schema import EvidenceChunk
from roleskills.evidence.store import EvidenceStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def store(temp_db):
    """Create a test store."""
    return EvidenceStore(temp_db)


@pytest.fixture
def sample_chunk():
    """Create a sample evidence chunk."""
    return EvidenceChunk(
        evidence_id="test123",
        repo="RoleSkills",
        owner="jaybea",
        commit="abc123",
        author="jaybea",
        path="src/main.py",
        start=10,
        end=20,
        text="def foo():\n    pass",
        lang="python",
        ownership=1.0,
        recency=0.9,
        quality=1.05,
        anchor="https://github.com/jaybea/RoleSkills/blob/abc123/src/main.py#L10-L20",
        created_at=datetime.now(timezone.utc),
    )


def test_store_init(temp_db):
    """Test store initialization."""
    store = EvidenceStore(temp_db)
    assert Path(temp_db).exists()


def test_upsert_single_chunk(store, sample_chunk):
    """Test inserting a single chunk."""
    n = store.upsert_chunks([sample_chunk])
    assert n == 1

    # Verify it was stored
    chunk = store.get_chunk("test123")
    assert chunk is not None
    assert chunk.evidence_id == "test123"
    assert chunk.repo == "RoleSkills"
    assert chunk.owner == "jaybea"


def test_upsert_multiple_chunks(store, sample_chunk):
    """Test inserting multiple chunks."""
    chunk2 = EvidenceChunk(
        evidence_id="test456",
        repo="AnotherRepo",
        owner="jaybea",
        commit="def456",
        author="jaybea",
        path="tests/test.py",
        start=1,
        end=5,
        text="def test():\n    pass",
        lang="python",
        ownership=1.0,
        recency=0.8,
        quality=1.1,
        anchor="https://github.com/jaybea/AnotherRepo/blob/def456/tests/test.py#L1-L5",
        created_at=datetime.now(timezone.utc),
    )

    n = store.upsert_chunks([sample_chunk, chunk2])
    assert n == 2

    stats = store.stats()
    assert stats["rows"] == 2


def test_upsert_replace(store, sample_chunk):
    """Test that upsert replaces existing chunks."""
    # Insert first time
    store.upsert_chunks([sample_chunk])

    # Create modified version with same ID
    modified_chunk = EvidenceChunk(
        evidence_id="test123",
        repo="RoleSkills",
        owner="jaybea",
        commit="xyz789",  # Different commit
        author="jaybea",
        path="src/main.py",
        start=10,
        end=20,
        text="def bar():\n    pass",  # Different text
        lang="python",
        ownership=1.0,
        recency=0.95,  # Different recency
        quality=1.1,  # Different quality
        anchor="https://github.com/jaybea/RoleSkills/blob/xyz789/src/main.py#L10-L20",
        created_at=datetime.now(timezone.utc),
    )

    # Upsert should replace
    store.upsert_chunks([modified_chunk])

    # Should still have only 1 row
    stats = store.stats()
    assert stats["rows"] == 1

    # Should have updated values
    chunk = store.get_chunk("test123")
    assert chunk.commit == "xyz789"
    assert chunk.text == "def bar():\n    pass"


def test_get_chunk_not_found(store):
    """Test getting a non-existent chunk."""
    chunk = store.get_chunk("nonexistent")
    assert chunk is None


def test_iter_chunks(store, sample_chunk):
    """Test iterating over chunks."""
    chunk2 = EvidenceChunk(
        evidence_id="test456",
        repo="RoleSkills",
        owner="jaybea",
        commit="def456",
        author="jaybea",
        path="tests/test.py",
        start=1,
        end=5,
        text="def test():\n    pass",
        lang="python",
        ownership=1.0,
        recency=0.8,
        quality=1.1,
        anchor="https://github.com/jaybea/RoleSkills/blob/def456/tests/test.py#L1-L5",
        created_at=datetime.now(timezone.utc),
    )

    store.upsert_chunks([sample_chunk, chunk2])

    chunks = list(store.iter_chunks())
    assert len(chunks) == 2


def test_iter_chunks_filter_repo(store, sample_chunk):
    """Test filtering chunks by repository."""
    chunk2 = EvidenceChunk(
        evidence_id="test456",
        repo="OtherRepo",
        owner="jaybea",
        commit="def456",
        author="jaybea",
        path="src/other.py",
        start=1,
        end=5,
        text="x = 1",
        lang="python",
        ownership=1.0,
        recency=0.8,
        quality=1.0,
        anchor="https://github.com/jaybea/OtherRepo/blob/def456/src/other.py#L1-L5",
        created_at=datetime.now(timezone.utc),
    )

    store.upsert_chunks([sample_chunk, chunk2])

    # Filter by repo
    chunks = list(store.iter_chunks(repo="RoleSkills"))
    assert len(chunks) == 1
    assert chunks[0].repo == "RoleSkills"


def test_iter_chunks_filter_quality(store, sample_chunk):
    """Test filtering chunks by quality threshold."""
    low_quality_chunk = EvidenceChunk(
        evidence_id="test456",
        repo="RoleSkills",
        owner="jaybea",
        commit="def456",
        author="jaybea",
        path="src/other.py",
        start=1,
        end=5,
        text="x = 1",
        lang="python",
        ownership=1.0,
        recency=0.8,
        quality=0.8,  # Lower quality
        anchor="https://github.com/jaybea/RoleSkills/blob/def456/src/other.py#L1-L5",
        created_at=datetime.now(timezone.utc),
    )

    store.upsert_chunks([sample_chunk, low_quality_chunk])

    # Filter by quality
    chunks = list(store.iter_chunks(min_quality=1.0))
    assert len(chunks) == 1
    assert chunks[0].quality >= 1.0


def test_iter_chunks_limit(store, sample_chunk):
    """Test limiting number of chunks returned."""
    # Create multiple chunks
    chunks = []
    for i in range(5):
        chunk = EvidenceChunk(
            evidence_id=f"test{i}",
            repo="RoleSkills",
            owner="jaybea",
            commit=f"commit{i}",
            author="jaybea",
            path=f"src/file{i}.py",
            start=1,
            end=5,
            text=f"x = {i}",
            lang="python",
            ownership=1.0,
            recency=0.8,
            quality=1.0,
            anchor=f"https://github.com/jaybea/RoleSkills/blob/commit{i}/src/file{i}.py#L1-L5",
            created_at=datetime.now(timezone.utc),
        )
        chunks.append(chunk)

    store.upsert_chunks(chunks)

    # Limit to 3
    limited = list(store.iter_chunks(limit=3))
    assert len(limited) == 3


def test_stats(store, sample_chunk):
    """Test statistics computation."""
    chunk2 = EvidenceChunk(
        evidence_id="test456",
        repo="OtherRepo",
        owner="jaybea",
        commit="def456",
        author="jaybea",
        path="tests/test.py",
        start=1,
        end=5,
        text="def test():\n    pass",
        lang="typescript",
        ownership=1.0,
        recency=0.7,
        quality=1.15,
        anchor="https://github.com/jaybea/OtherRepo/blob/def456/tests/test.py#L1-L5",
        created_at=datetime.now(timezone.utc),
    )

    store.upsert_chunks([sample_chunk, chunk2])

    stats = store.stats()
    assert stats["rows"] == 2
    assert stats["repos"] == 2  # RoleSkills and OtherRepo
    assert stats["languages"] == 2  # python and typescript
    assert 0.8 <= stats["avg_recency"] <= 0.85  # (0.9 + 0.7) / 2 = 0.8
    assert 1.09 <= stats["avg_quality"] <= 1.11  # (1.05 + 1.15) / 2 = 1.1


def test_stats_empty(store):
    """Test statistics on empty database."""
    stats = store.stats()
    assert stats["rows"] == 0
    assert stats["avg_quality"] == 0
    assert stats["avg_recency"] == 0
    assert stats["repos"] == 0
    assert stats["languages"] == 0


def test_clear(store, sample_chunk):
    """Test clearing the database."""
    store.upsert_chunks([sample_chunk])
    assert store.stats()["rows"] == 1

    store.clear()
    assert store.stats()["rows"] == 0


def test_fts_triggers(store, sample_chunk):
    """Test that FTS5 triggers keep index in sync."""
    # Insert chunk
    store.upsert_chunks([sample_chunk])

    # Check FTS table has the entry
    with store._conn() as con:
        cur = con.execute("SELECT COUNT(*) FROM evidence_fts")
        (fts_count,) = cur.fetchone()
        assert fts_count == 1

    # Delete chunk
    with store._conn() as con:
        con.execute("DELETE FROM evidence WHERE evidence_id = ?", ("test123",))

    # Check FTS table is also updated
    with store._conn() as con:
        cur = con.execute("SELECT COUNT(*) FROM evidence_fts")
        (fts_count,) = cur.fetchone()
        assert fts_count == 0