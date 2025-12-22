"""Tests for quality scoring."""


from roleskills.evidence.quality import compute_quality


def test_quality_base():
    """Test base quality score."""
    q = compute_quality("src/main.py", "x = 1")
    assert q == 1.0


def test_quality_test_file():
    """Test quality bonus for test files."""
    q = compute_quality("tests/test_api.py", "def test_foo(): pass")
    assert q == 1.1  # +0.10 for tests


def test_quality_ci_file():
    """Test quality bonus for CI/CD files."""
    q = compute_quality(".github/workflows/ci.yml", "name: CI")
    assert q == 1.05  # +0.05 for CI


def test_quality_type_hints():
    """Test quality bonus for type hints."""
    code = """
def foo(x: int) -> str:
    return str(x)
"""
    q = compute_quality("src/main.py", code)
    assert q == 1.05  # +0.05 for type hints


def test_quality_docstrings():
    """Test quality bonus for docstrings."""
    code = '''
def foo():
    """This is a docstring."""
    pass
'''
    q = compute_quality("src/main.py", code)
    assert q == 1.03  # +0.03 for docstrings


def test_quality_comments():
    """Test quality bonus for comments."""
    code = """
# This is a helpful comment
def foo():
    pass
"""
    q = compute_quality("src/main.py", code)
    assert q == 1.03  # +0.03 for comments


def test_quality_complexity_decrease():
    """Test quality bonus for reducing complexity."""
    q = compute_quality("src/main.py", "x = 1", complexity_delta=-2)
    assert q == 1.05  # +0.05 for complexity reduction


def test_quality_complexity_increase():
    """Test quality penalty for increasing complexity."""
    q = compute_quality("src/main.py", "x = 1", complexity_delta=5)
    assert q == 0.95  # -0.05 for complexity increase


def test_quality_large_addition():
    """Test quality penalty for large additions."""
    q = compute_quality("src/main.py", "x = 1", add_del_ratio=5.0)
    assert q == 0.95  # -0.05 for large add/del ratio


def test_quality_commit_message():
    """Test quality bonus for good commit message."""
    q = compute_quality("src/main.py", "x = 1", commit_message="fix: resolve bug")
    assert q == 1.05  # +0.05 for fix


def test_quality_combined():
    """Test combined quality bonuses."""
    code = '''
def test_api(x: int) -> None:
    """Test the API."""
    assert x > 0
'''
    q = compute_quality(
        "tests/test_api.py",
        code,
        commit_message="refactor: improve test",
    )
    # +0.10 (tests) +0.05 (type hints) +0.03 (docstring) +0.05 (commit) = 1.23
    # But clamped to 1.2
    assert q == 1.2


def test_quality_floor():
    """Test quality floor (minimum 0.5)."""
    # Even with penalties, should not go below 0.5
    q = compute_quality(
        "src/main.py",
        "x = 1",
        complexity_delta=10,
        add_del_ratio=10.0,
    )
    assert q >= 0.5