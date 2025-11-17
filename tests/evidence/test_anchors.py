"""Tests for GitHub permalink generation."""

import pytest

from roleskills.evidence.anchors import github_commit_anchor


def test_anchor_basic():
    """Test basic anchor generation."""
    anchor = github_commit_anchor(
        "jaybea", "RoleSkills", "abc123", "src/main.py", 10, 25
    )
    assert anchor == "https://github.com/jaybea/RoleSkills/blob/abc123/src/main.py#L10-L25"


def test_anchor_single_line():
    """Test anchor for single line (no range)."""
    anchor = github_commit_anchor(
        "jaybea", "RoleSkills", "abc123", "src/main.py", 10, 10
    )
    assert anchor == "https://github.com/jaybea/RoleSkills/blob/abc123/src/main.py#L10"


def test_anchor_org_repo():
    """Test anchor with organization."""
    anchor = github_commit_anchor(
        "ammons-datalabs", "project", "def456", "tests/test_api.py", 5, 15
    )
    assert (
        anchor
        == "https://github.com/ammons-datalabs/project/blob/def456/tests/test_api.py#L5-L15"
    )


def test_anchor_nested_path():
    """Test anchor with nested path."""
    anchor = github_commit_anchor(
        "jaybea", "repo", "xyz789", "src/api/handlers/auth.py", 100, 120
    )
    assert (
        anchor
        == "https://github.com/jaybea/repo/blob/xyz789/src/api/handlers/auth.py#L100-L120"
    )