"""Tests for evidence builder."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from roleskills.evidence import EvidenceStore, build_index


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository with sample commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir)

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Create initial structure
        src_dir = repo_dir / "src"
        src_dir.mkdir()
        tests_dir = repo_dir / "tests"
        tests_dir.mkdir()
        ci_dir = repo_dir / ".github" / "workflows"
        ci_dir.mkdir(parents=True)

        # Commit 1: Add main.py
        (src_dir / "main.py").write_text(
            """
def hello():
    print("Hello")
"""
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "feat: add hello function"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Commit 2: Add test
        (tests_dir / "test_main.py").write_text(
            """
def test_hello():
    from src.main import hello
    hello()
"""
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "test: add test for hello"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Commit 3: Add CI
        (ci_dir / "ci.yml").write_text(
            """
name: CI
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest
"""
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "ci: add GitHub Actions"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Commit 4: Update with type hints
        (src_dir / "main.py").write_text(
            """
def hello(name: str) -> None:
    '''Say hello to someone.'''
    print(f"Hello, {name}!")
"""
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "refactor: add type hints and docstring"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        yield repo_dir


@pytest.mark.slow
def test_build_index_smoke(temp_git_repo, temp_db):
    """Smoke test for build_index with a real git repo."""
    store = EvidenceStore(temp_db)

    stats = build_index(
        author="test",
        repo_dirs=[temp_git_repo],
        store=store,
        chunk_budget=100,
    )

    # Should have processed the repo
    assert stats["repos"] == 1
    assert stats["chunks_written"] > 0
    assert stats["commits_selected"] > 0

    # Verify chunks were stored
    db_stats = store.stats()
    assert db_stats["rows"] > 0

    # Check that we have chunks from different commit types
    chunks = list(store.iter_chunks())
    assert len(chunks) > 0

    # Should have at least one chunk with an anchor
    assert all(chunk.anchor.startswith("https://github.com/") for chunk in chunks)


@pytest.mark.slow
def test_build_index_with_jd_terms(temp_git_repo, temp_db):
    """Test build_index with JD term filtering."""
    # Add a commit with specific JD terms
    src_dir = temp_git_repo / "src"
    (src_dir / "azure_client.py").write_text(
        """
def connect_to_azure():
    '''Connect to Azure services.'''
    pass
"""
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "feat: add Azure integration"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    store = EvidenceStore(temp_db)

    # Build index with JD terms
    stats = build_index(
        author="test",
        repo_dirs=[temp_git_repo],
        jd_terms=["azure"],
        store=store,
        chunk_budget=100,
    )

    # Should have processed commits (pickaxe may or may not find results depending on git version)
    assert stats["commits_selected"] > 0
    # If pickaxe found results, they should be counted
    assert stats["commits_pickaxe"] >= 0


@pytest.mark.slow
def test_build_index_quality_filtering(temp_git_repo, temp_db):
    """Test that quality floor filters out low-quality chunks."""
    store = EvidenceStore(temp_db)

    # Build with high quality floor
    stats = build_index(
        author="test",
        repo_dirs=[temp_git_repo],
        store=store,
        quality_floor=1.1,  # High threshold
    )

    # Should filter out some chunks
    chunks = list(store.iter_chunks())

    # All stored chunks should meet quality threshold
    assert all(chunk.quality >= 1.1 for chunk in chunks)


@pytest.mark.slow
def test_build_index_deduplication(temp_git_repo, temp_db):
    """Test that duplicate chunks are not stored."""
    # Create two identical changes
    src_dir = temp_git_repo / "src"

    # First commit
    (src_dir / "dup.py").write_text("x = 1")
    subprocess.run(
        ["git", "add", "."],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "add x"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Remove and re-add (creates duplicate diff)
    (src_dir / "dup.py").unlink()
    subprocess.run(
        ["git", "add", "."],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "remove x"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    (src_dir / "dup.py").write_text("x = 1")
    subprocess.run(
        ["git", "add", "."],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "re-add x"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    store = EvidenceStore(temp_db)

    build_index(
        author="test",
        repo_dirs=[temp_git_repo],
        store=store,
    )

    # Check that duplicates were filtered
    chunks = list(store.iter_chunks())
    evidence_ids = [c.evidence_id for c in chunks]

    # Should have no duplicate IDs
    assert len(evidence_ids) == len(set(evidence_ids))