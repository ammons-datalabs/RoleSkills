"""
Deterministic quality scoring for evidence chunks.
"""

import os
import re


def compute_quality(
    path: str,
    text: str,
    *,
    commit_message: str = "",
    add_del_ratio: float | None = None,
    complexity_delta: int | None = None,
) -> float:
    """
    Compute deterministic quality score for a code chunk.

    Args:
        path: File path
        text: Code content
        commit_message: Commit message (optional)
        add_del_ratio: Ratio of additions to deletions (optional)
        complexity_delta: Change in cyclomatic complexity (optional)

    Returns:
        Quality score in range [0.5, 1.2]

    Scoring heuristics:
        Base: 1.0
        +0.10 if tests
        +0.05 if CI/CD
        +0.05 if type hints/annotations
        +0.03 if docstrings/comments
        +0.05 if complexity decreases
        +0.05 if commit message indicates quality intent
        -0.05 if complexity increases significantly
        -0.05 if additions >> deletions (>3x)

    Example:
        >>> compute_quality("tests/test_api.py", "def test_foo():\\n    pass")
        1.1
        >>> compute_quality("src/main.py", "x = 1")
        1.0
    """
    q = 1.0
    base = os.path.basename(path)

    # Tests: +0.10
    if path.startswith("tests/") or base.startswith("test_"):
        q += 0.10

    # CI/CD: +0.05
    if (
        ".github/workflows/" in path
        or base in {"azure-pipelines.yml", "Dockerfile", ".gitlab-ci.yml"}
    ):
        q += 0.05

    # Type hints / returns: +0.05
    if "def " in text and re.search(r":\s*[\w\[\],\.]+", text) and "->" in text:
        q += 0.05

    # Docstrings / comments: +0.03
    if '"""' in text or re.search(r"^\s*# ", text, re.MULTILINE):
        q += 0.03

    # Complexity delta
    if complexity_delta is not None:
        if complexity_delta < 0:
            q += 0.05  # Reduced complexity
        elif complexity_delta > 1:
            q -= 0.05  # Increased complexity

    # Size heuristics
    if add_del_ratio is not None and add_del_ratio > 3:
        q -= 0.05  # Lots of additions, few deletions (may be boilerplate)

    # Commit intent
    if re.search(r"\b(test|fix|refactor)\b", commit_message, re.IGNORECASE):
        q += 0.05

    # Clamp to [0.5, 1.2]
    return max(0.5, min(round(q, 2), 1.2))