"""Tests for JD preprocessing."""

from roleskills.jd.preprocess import clean_jd_text


def test_clean_jd_text_strips_html():
    """Test that HTML tags are removed."""
    html = "<p>Hello <b>world</b></p><div>Test content</div>"
    cleaned = clean_jd_text(html)
    assert "<p>" not in cleaned
    assert "<b>" not in cleaned
    assert "Hello" in cleaned
    assert "world" in cleaned


def test_clean_jd_text_normalizes_whitespace():
    """Test that excessive whitespace is normalized."""
    text = "Hello    world\n\n\n\nTest    content"
    cleaned = clean_jd_text(text)
    assert "    " not in cleaned  # Multiple spaces removed
    assert "Hello world" in cleaned


def test_clean_jd_text_removes_footer_noise():
    """Test that common footer text is removed."""
    text = """
    Senior Python Engineer

    Requirements:
    - Python experience
    - 5+ years

    Privacy Policy
    Terms of Service
    LinkedIn Corporation © 2024
    """
    cleaned = clean_jd_text(text)
    assert "Python experience" in cleaned
    assert "Privacy Policy" not in cleaned
    assert "LinkedIn Corporation" not in cleaned


def test_clean_jd_text_realistic_case():
    """Test with a realistic JD snippet to see what LLM receives."""
    text = """
    <h1>Integration Developer</h1>
    <h2>About the job</h2>
    <p>ACME Digital Solutions are experts in digital business enablement.</p>

    <h2>Requirements</h2>
    <ul>
      <li>Must have: Python, FastAPI, and experience with Azure.</li>
      <li>Strong experience with Docker and GitHub Actions.</li>
    </ul>

    <footer>
      Privacy Policy | Terms of Service
      © Copyright 2024 ACME Corp
    </footer>
    """

    cleaned = clean_jd_text(text)

    # Should remove HTML
    assert "<h1>" not in cleaned
    assert "<ul>" not in cleaned

    # Should keep content
    assert "Integration Developer" in cleaned
    assert "ACME Digital Solutions" in cleaned
    assert "Python, FastAPI" in cleaned
    assert "Docker and GitHub Actions" in cleaned

    # Should remove footer
    assert "Privacy Policy" not in cleaned
    assert "Copyright 2024" not in cleaned

    # Print what LLM would actually see
    print("\n" + "="*60)
    print("CLEANED TEXT THAT GOES TO LLM:")
    print("="*60)
    print(cleaned)
    print("="*60)


def test_clean_jd_text_handles_plain_text():
    """Test that plain text (no HTML) passes through cleanly."""
    text = """
    # Senior Python Engineer
    ## Requirements
    - Must have: Python, FastAPI
    - Strong experience with Docker
    """
    cleaned = clean_jd_text(text)
    assert "Senior Python Engineer" in cleaned
    assert "Python, FastAPI" in cleaned