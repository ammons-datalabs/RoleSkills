"""
Evidence index builder - orchestrates discovery, chunking, and storage.
"""

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from math import exp
from pathlib import Path
from typing import Any

from .anchors import github_commit_anchor
from .chunks import iter_diff_hunks, normalize_text
from .filters import DEFAULT_ALLOW, DEFAULT_DENY, is_allowed
from .github import (
    get_commit_meta,
    get_commit_patch,
    get_diff_stats,
    get_owner_repo,
    is_commit_pushed,
    pickaxe_commits,
    recent_commits,
    stratified_commits,
)
from .quality import compute_quality
from .schema import EvidenceChunk
from .store import EvidenceStore


def build_index(
    author: str,
    *,
    preferred_orgs: set[str] | None = None,
    jd_terms: list[str] | None = None,
    chunk_budget: int = 3000,
    recent_window: str = "180 days",
    store: EvidenceStore | None = None,
    repo_dirs: list[Path] | None = None,
    allow: list[str] | None = None,
    deny: list[str] | None = None,
    max_chunk_lines: int = 40,
    quality_floor: float = 0.8,
    per_file_cap: int = 5,
    per_commit_cap: int = 10,
) -> dict[str, Any]:
    """
    Build evidence index from git repositories.

    Discovery strategy:
    1. Pickaxe search for JD-relevant commits (if jd_terms provided)
    2. Stratified time sampling for historical coverage
    3. Recent commits for current stack

    Args:
        author: GitHub username to attribute (e.g., "jaybea")
        preferred_orgs: Organizations to boost ownership score
        jd_terms: Terms to search for via pickaxe (e.g., ["azure", "fastapi"])
        chunk_budget: Maximum chunks to store (default 3000)
        recent_window: Time window for recent commits (e.g., "180 days")
        store: EvidenceStore instance (creates default if None)
        repo_dirs: Repositories to scan (defaults to current directory)
        allow: Path patterns to include
        deny: Path patterns to exclude
        max_chunk_lines: Maximum lines per chunk
        quality_floor: Minimum quality to store (0-1.2)
        per_file_cap: Max chunks per file
        per_commit_cap: Max chunks per commit

    Returns:
        Statistics dictionary with:
        - chunks_written: Number of chunks stored
        - repos: Number of repositories scanned
        - commits_selected: Number of commits processed
        - commits_pickaxe: Number from pickaxe search
        - commits_stratified: Number from time sampling
        - commits_recent: Number from recent window

    Example:
        >>> from roleskills.evidence import build_index, EvidenceStore
        >>> store = EvidenceStore("index.sqlite")
        >>> stats = build_index(
        ...     author="jaybea",
        ...     preferred_orgs={"ammons-datalabs"},
        ...     jd_terms=["azure", "fastapi", "pytest"],
        ...     store=store,
        ... )
        >>> stats["chunks_written"]
        642
    """
    # Set defaults
    if preferred_orgs is None:
        preferred_orgs = set()
    if jd_terms is None:
        jd_terms = []
    if store is None:
        store = EvidenceStore()
    if repo_dirs is None:
        repo_dirs = [Path.cwd()]
    if allow is None:
        allow = DEFAULT_ALLOW
    if deny is None:
        deny = DEFAULT_DENY

    # Convert JD terms to regex patterns
    jd_patterns = [rf"\b{term}\b" for term in jd_terms] if jd_terms else []

    # Track stats
    stats = {
        "chunks_written": 0,
        "repos": 0,
        "commits_selected": 0,
        "commits_pickaxe": 0,
        "commits_stratified": 0,
        "commits_recent": 0,
        "commits_unpushed": 0,
    }

    # Process each repository
    for repo_dir in repo_dirs:
        if not repo_dir.exists() or not (repo_dir / ".git").exists():
            continue

        stats["repos"] += 1
        owner, repo = get_owner_repo(repo_dir)

        # === Phase 1: Commit Discovery ===
        selected_commits = set()

        # Pickaxe search (JD-aware)
        if jd_patterns:
            pickaxe_shas = pickaxe_commits(repo_dir, jd_patterns, allow)
            selected_commits.update(pickaxe_shas)
            stats["commits_pickaxe"] += len(pickaxe_shas)

        # Stratified sampling (historical coverage)
        stratified_shas = stratified_commits(repo_dir, per_bucket=10)
        selected_commits.update(stratified_shas)
        stats["commits_stratified"] += len(stratified_shas)

        # Recent commits (current stack)
        recent_shas = recent_commits(repo_dir, since=recent_window)
        selected_commits.update(recent_shas)
        stats["commits_recent"] += len(recent_shas)

        stats["commits_selected"] += len(selected_commits)

        # Check for unpushed commits
        unpushed_shas = {
            sha for sha in selected_commits if not is_commit_pushed(repo_dir, sha)
        }
        stats["commits_unpushed"] += len(unpushed_shas)

        # === Phase 2: Chunk Extraction & Feature Engineering ===
        chunks: list[EvidenceChunk] = []
        seen_hashes = set()
        file_counts: dict[str, int] = defaultdict(int)
        commit_counts: dict[str, int] = defaultdict(int)

        for sha in selected_commits:
            # Respect per-commit cap
            if commit_counts[sha] >= per_commit_cap:
                continue

            try:
                # Get commit data
                patch = get_commit_patch(repo_dir, sha, context_lines=8)
                commit_msg, commit_date = get_commit_meta(repo_dir, sha)
                additions, deletions = get_diff_stats(patch)
                add_del_ratio = (
                    additions / max(1, deletions) if deletions > 0 else None
                )

                # Extract hunks
                for path, start, end, text in iter_diff_hunks(patch, max_chunk_lines):
                    # Apply filters
                    if not is_allowed(path, allow, deny):
                        continue

                    # Respect per-file cap
                    if file_counts[path] >= per_file_cap:
                        continue

                    # De-duplication
                    normalized = normalize_text(text)
                    content_hash = hashlib.sha1(normalized.encode()).hexdigest()

                    if content_hash in seen_hashes:
                        continue
                    seen_hashes.add(content_hash)

                    # Compute features
                    ownership = _compute_ownership(author, owner, preferred_orgs)
                    recency = _compute_recency(commit_date)
                    quality = compute_quality(
                        path,
                        text,
                        commit_message=commit_msg,
                        add_del_ratio=add_del_ratio,
                    )

                    # Apply quality floor
                    if quality < quality_floor:
                        continue

                    # Detect language
                    lang = _detect_language(path)

                    # Generate anchor
                    anchor = github_commit_anchor(owner, repo, sha, path, start, end)

                    # Create chunk
                    chunk = EvidenceChunk(
                        evidence_id=content_hash,
                        repo=repo,
                        owner=owner,
                        commit=sha,
                        author=author,
                        path=path,
                        start=start,
                        end=end,
                        text=text,
                        lang=lang,
                        ownership=ownership,
                        recency=recency,
                        quality=quality,
                        anchor=anchor,
                        created_at=datetime.now(timezone.utc),
                    )

                    chunks.append(chunk)
                    file_counts[path] += 1
                    commit_counts[sha] += 1

                    # Stop if budget reached
                    if len(chunks) >= chunk_budget:
                        break

            except Exception:
                # Skip commits that fail to process
                continue

            # Stop if budget reached
            if len(chunks) >= chunk_budget:
                break

        # === Phase 3: Store ===
        written = store.upsert_chunks(chunks)
        stats["chunks_written"] += written

    return stats


def _compute_ownership(
    author: str, owner: str, preferred_orgs: set[str]
) -> float:
    """
    Compute ownership multiplier.

    Rules:
    - Own repo: 1.0
    - Preferred org repo: 1.2
    - External repo: 0.7

    Args:
        author: Author username
        owner: Repository owner
        preferred_orgs: Set of preferred organization names

    Returns:
        Ownership score (0.7-1.2)
    """
    if owner == author:
        return 1.0
    if owner in preferred_orgs:
        return 1.2
    return 0.7


def _compute_recency(commit_date: datetime) -> float:
    """
    Compute exponential recency score.

    Uses exponential decay with τ=365 days:
    recency = exp(-age_days / 365)

    Args:
        commit_date: Commit timestamp

    Returns:
        Recency score (0-1)
    """
    now = datetime.now(timezone.utc)
    age_days = (now - commit_date).days
    return round(exp(-age_days / 365.0), 3)


def _detect_language(path: str) -> str | None:
    """
    Detect programming language from file extension.

    Args:
        path: File path

    Returns:
        Language name or None
    """
    ext_map = {
        "py": "python",
        "ts": "typescript",
        "js": "javascript",
        "tsx": "typescript",
        "jsx": "javascript",
        "md": "markdown",
        "mmd": "mermaid",
        "yml": "yaml",
        "yaml": "yaml",
        "json": "json",
        "toml": "toml",
        "sh": "shell",
        "bash": "shell",
        "rs": "rust",
        "go": "go",
        "java": "java",
        "c": "c",
        "cpp": "cpp",
        "h": "c",
        "hpp": "cpp",
    }

    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return ext_map.get(ext)