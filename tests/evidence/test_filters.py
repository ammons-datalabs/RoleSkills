"""Tests for path filtering."""


from roleskills.evidence.filters import is_allowed


def test_allow_src():
    """Test that src/** files are allowed."""
    assert is_allowed("src/main.py")
    assert is_allowed("src/api/handlers.py")


def test_allow_tests():
    """Test that tests/** files are allowed."""
    assert is_allowed("tests/test_api.py")
    assert is_allowed("tests/integration/test_flows.py")


def test_allow_docs():
    """Test that docs/** files are allowed."""
    assert is_allowed("docs/README.md")
    assert is_allowed("docs/architecture.mmd")


def test_deny_vendor():
    """Test that vendor code is denied."""
    assert not is_allowed("vendor/lib.py")


def test_deny_dist():
    """Test that build artifacts are denied."""
    assert not is_allowed("dist/bundle.js")
    assert not is_allowed("build/output.js")


def test_deny_lockfiles():
    """Test that lockfiles are denied."""
    assert not is_allowed("package-lock.json")
    assert not is_allowed("poetry.lock")


def test_deny_minified():
    """Test that minified files are denied."""
    assert not is_allowed("static/app.min.js")
    assert not is_allowed("css/style.min.css")


def test_deny_images():
    """Test that image files are denied."""
    assert not is_allowed("assets/logo.png")
    assert not is_allowed("images/screenshot.jpg")


def test_deny_pycache():
    """Test that __pycache__ is denied."""
    assert not is_allowed("src/__pycache__/main.cpython-311.pyc")


def test_custom_allow():
    """Test custom allow patterns."""
    assert is_allowed("custom/file.py", allow=["custom/**"])
    assert not is_allowed("custom/file.py", allow=["src/**"])


def test_custom_deny():
    """Test custom deny patterns."""
    assert not is_allowed("src/bad.py", deny=["**/bad.py"])
    assert is_allowed("src/good.py", deny=["**/bad.py"])


def test_deny_takes_precedence():
    """Test that deny patterns override allow patterns."""
    # Even if allowed by pattern, deny should win
    assert not is_allowed("src/vendor/lib.py", allow=["src/**"], deny=["**/vendor/**"])