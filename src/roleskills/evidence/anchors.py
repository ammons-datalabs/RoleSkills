"""
GitHub permalink (anchor) generation for evidence chunks.
"""


def github_commit_anchor(
    owner: str, repo: str, commit: str, path: str, start: int, end: int
) -> str:
    """
    Generate stable GitHub permalink to specific lines in a commit.

    Args:
        owner: Repository owner/org
        repo: Repository name
        commit: Git commit SHA
        path: File path relative to repo root
        start: Starting line number
        end: Ending line number

    Returns:
        URL like: https://github.com/owner/repo/blob/commit/path#L10-L25

    Example:
        >>> github_commit_anchor("ammons-datalabs", "project", "abc123", "src/main.py", 10, 25)
        'https://github.com/ammons-datalabs/project/blob/abc123/src/main.py#L10-L25'
    """
    end_part = f"-L{end}" if end and end > start else ""
    return f"https://github.com/{owner}/{repo}/blob/{commit}/{path}#L{start}{end_part}"