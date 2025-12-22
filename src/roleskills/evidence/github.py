"""
Git/GitHub discovery and commit selection.
"""

import re
import subprocess  # nosec B404 - git is a trusted binary
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _git(repo_dir: Path, *args: str) -> str:
    """
    Execute git command and return stdout.

    Args:
        repo_dir: Path to git repository
        *args: Git command arguments

    Returns:
        Command output as string

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    return subprocess.check_output(  # nosec B603 B607 - git with fixed args
        ["git", *args],
        cwd=repo_dir,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def pickaxe_commits(
    repo_dir: Path, patterns: list[str], paths: list[str] | None = None
) -> set[str]:
    """
    Find commits that mention specific patterns (JD-aware discovery).

    Uses git log -G to find commits where diffs contain pattern matches.
    This enables jumping to old but relevant commits for specific skills.

    Args:
        repo_dir: Path to git repository
        patterns: Regex patterns to search for (e.g., ["\\bazure\\b", "\\bfastapi\\b"])
        paths: Optional list of paths to constrain search (e.g., ["src/**", "tests/**"])

    Returns:
        Set of commit SHAs

    Example:
        >>> pickaxe_commits(Path("."), ["azure", "fastapi"], ["src/**"])
        {'abc123...', 'def456...'}
    """
    if paths is None:
        paths = ["src/**", "tests/**", "docs/**"]

    shas = set()
    for pat in patterns:
        try:
            # -G searches for changes that match the pattern
            # --all searches all branches
            # --date-order orders by commit date
            cmd = ["log", "--all", "--date-order", "-G", pat, "--pretty=%H", "--"]
            cmd.extend(paths)
            out = _git(repo_dir, *cmd)
            if out:
                shas.update(out.splitlines())
        except subprocess.CalledProcessError:
            # Pattern may not match anything, continue
            continue

    return shas


def stratified_commits(repo_dir: Path, per_bucket: int = 10) -> set[str]:
    """
    Sample commits across time to ensure historical coverage.

    Groups commits by month and samples N per month. This prevents
    recency bias and ensures representative coverage of tech stack evolution.

    Args:
        repo_dir: Path to git repository
        per_bucket: Number of commits to sample per time bucket (default 10)

    Returns:
        Set of commit SHAs

    Example:
        >>> stratified_commits(Path("."), per_bucket=5)
        {'abc123...', 'def456...', ...}
    """
    try:
        # Get all commits with dates (YYYY-MM-DD format)
        out = _git(repo_dir, "log", "--all", "--date=short", "--pretty=%ad %H")
    except subprocess.CalledProcessError:
        return set()

    if not out:
        return set()

    # Group by year-month
    buckets: dict[str, list[str]] = defaultdict(list)
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            date, sha = parts[0], parts[1]
            ym = date[:7]  # YYYY-MM
            buckets[ym].append(sha)

    # Sample from each bucket
    sampled = set()
    for ym, shas in buckets.items():
        sampled.update(shas[:per_bucket])

    return sampled


def recent_commits(repo_dir: Path, since: str = "180 days") -> set[str]:
    """
    Get recent commits within a time window.

    Args:
        repo_dir: Path to git repository
        since: Time window (e.g., "180 days", "6 months", "1 year")

    Returns:
        Set of commit SHAs

    Example:
        >>> recent_commits(Path("."), since="90 days")
        {'abc123...', 'def456...'}
    """
    try:
        out = _git(repo_dir, "log", f"--since={since}", "--pretty=%H")
    except subprocess.CalledProcessError:
        return set()

    if not out:
        return set()

    return set(out.splitlines())


def get_commit_patch(repo_dir: Path, sha: str, context_lines: int = 8) -> str:
    """
    Get unified diff patch for a commit.

    Args:
        repo_dir: Path to git repository
        sha: Commit SHA
        context_lines: Lines of context around changes (default 8)

    Returns:
        Unified diff patch as string

    Example:
        >>> patch = get_commit_patch(Path("."), "abc123")
        >>> "diff --git" in patch
        True
    """
    return _git(repo_dir, "show", f"--unified={context_lines}", "--patch", sha)


def get_commit_meta(repo_dir: Path, sha: str) -> tuple[str, datetime]:
    """
    Get commit metadata (message and date).

    Args:
        repo_dir: Path to git repository
        sha: Commit SHA

    Returns:
        Tuple of (commit_message, commit_date)

    Example:
        >>> msg, dt = get_commit_meta(Path("."), "abc123")
        >>> isinstance(dt, datetime)
        True
    """
    msg = _git(repo_dir, "log", "-1", "--pretty=%B", sha)
    date_str = _git(repo_dir, "log", "-1", "--pretty=%cI", sha)

    # Parse ISO 8601 date
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    return msg, dt


def get_owner_repo(repo_dir: Path) -> tuple[str, str]:
    """
    Extract owner and repo name from git remote.

    Args:
        repo_dir: Path to git repository

    Returns:
        Tuple of (owner, repo_name)

    Example:
        >>> get_owner_repo(Path("."))
        ('jaybea', 'RoleSkills')
    """
    try:
        remote = _git(repo_dir, "remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        # No remote, use directory name
        return ("unknown", repo_dir.name)

    # Parse GitHub URL patterns:
    # https://github.com/owner/repo.git
    # git@github.com:owner/repo.git
    m = re.search(r"github\.com[:/](.+?)/(.+?)(?:\.git)?$", remote)
    if m:
        return (m.group(1), m.group(2).rstrip(".git"))

    return ("unknown", repo_dir.name)


def get_diff_stats(patch: str) -> tuple[int, int]:
    """
    Extract addition/deletion counts from a patch.

    Args:
        patch: Unified diff patch

    Returns:
        Tuple of (additions, deletions)

    Example:
        >>> get_diff_stats("...\n+foo\n+bar\n-baz\n")
        (2, 1)
    """
    additions = 0
    deletions = 0

    for line in patch.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    return additions, deletions


def is_commit_pushed(repo_dir: Path, sha: str) -> bool:
    """
    Check if a commit exists on any remote branch.

    Args:
        repo_dir: Path to git repository
        sha: Commit SHA to check

    Returns:
        True if commit is on a remote branch, False otherwise
    """
    try:
        # Check if commit is reachable from any remote branch
        result = _git(repo_dir, "branch", "-r", "--contains", sha)
        return bool(result.strip())
    except subprocess.CalledProcessError:
        return False