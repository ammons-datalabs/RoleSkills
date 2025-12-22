"""Tests for LLM JD parser."""

from pathlib import Path
from unittest.mock import Mock, patch
import json
import os
import pytest

from roleskills.jd.llm_parser import llm_parse_jd
from roleskills.jd.schema import JD

DATA = Path(__file__).parents[1] / "data"


def test_llm_parse_jd_requires_api_key():
    """Test that missing API key raises friendly error."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove any existing OPENAI_API_KEY
        os.environ.pop("OPENAI_API_KEY", None)

        with pytest.raises(ValueError) as exc_info:
            llm_parse_jd("test text")

        assert "OPENAI_API_KEY" in str(exc_info.value)
        assert "not set" in str(exc_info.value)


def test_llm_parse_jd_prompt_construction(monkeypatch, tmp_path):
    """Test what actually gets sent to the LLM - useful for debugging."""
    # Mock the cache directory to avoid pollution
    monkeypatch.setattr("roleskills.jd.llm_parser.CACHE_DIR", tmp_path)

    # Set fake API key
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    # Read a real test JD
    jd_text = (DATA / "jd1.md").read_text()

    # Mock OpenAI client to capture the prompt
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "role": "Senior Python Engineer",
        "title": None,
        "requirements": [
            {
                "id": "test-1",
                "title": "Python",
                "weight": "must",
                "tags": ["python"],
                "source_text": "Must have: Python",
                "section": "requirements"
            }
        ]
    })

    captured_prompt = None

    def mock_create(**kwargs):
        nonlocal captured_prompt
        captured_prompt = kwargs["messages"][0]["content"]
        return mock_response

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = Mock()
        mock_client.chat.completions.create = mock_create
        MockOpenAI.return_value = mock_client

        result = llm_parse_jd(jd_text, use_cache=False)

        # Verify we got a result
        assert result.role == "Senior Python Engineer"
        assert len(result.requirements) == 1

        # Print the actual prompt for visibility
        print("\n" + "="*80)
        print("ACTUAL PROMPT SENT TO LLM:")
        print("="*80)
        print(captured_prompt)
        print("="*80)

        # Verify prompt contains key elements
        assert captured_prompt is not None
        assert "TEXT" in captured_prompt
        assert "PREPARSED" in captured_prompt
        assert "Python" in captured_prompt
        assert "must|strong|nice" in captured_prompt

        # Verify deterministic pre-parse is included and not empty
        assert '"requirements"' in captured_prompt
        assert "FastAPI" in captured_prompt  # Should be in preparsed requirements
        assert "Docker" in captured_prompt   # Should be in preparsed requirements


def test_llm_parse_jd_uses_cache(monkeypatch, tmp_path):
    """Test that caching works - second call doesn't hit OpenAI."""
    monkeypatch.setattr("roleskills.jd.llm_parser.CACHE_DIR", tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    jd_text = "Test JD"
    cached_result = {
        "role": "Test Role",
        "title": None,
        "requirements": []
    }

    # Pre-populate cache
    import hashlib
    from roleskills.jd.preprocess import clean_jd_text
    cleaned = clean_jd_text(jd_text)
    cache_key = hashlib.sha1(cleaned.encode()).hexdigest()
    cache_path = tmp_path / f"{cache_key}.json"
    cache_path.write_text(json.dumps(cached_result))

    # This should NOT call OpenAI (no mock needed)
    result = llm_parse_jd(jd_text, use_cache=True)

    assert result.role == "Test Role"
    assert len(result.requirements) == 0


def test_llm_parse_jd_can_bypass_cache(monkeypatch, tmp_path):
    """Test that use_cache=False bypasses cache."""
    monkeypatch.setattr("roleskills.jd.llm_parser.CACHE_DIR", tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    jd_text = "Test JD"

    # Pre-populate cache with stale data
    import hashlib
    from roleskills.jd.preprocess import clean_jd_text
    cleaned = clean_jd_text(jd_text)
    cache_key = hashlib.sha1(cleaned.encode()).hexdigest()
    cache_path = tmp_path / f"{cache_key}.json"
    cache_path.write_text(json.dumps({"role": "Stale", "title": None, "requirements": []}))

    # Mock OpenAI to return fresh data
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "role": "Fresh",
        "title": None,
        "requirements": []
    })

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = Mock()
        mock_client.chat.completions.create = Mock(return_value=mock_response)
        MockOpenAI.return_value = mock_client

        result = llm_parse_jd(jd_text, use_cache=False)

        # Should get fresh result, not cached
        assert result.role == "Fresh"


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY for live integration test"
)
def test_llm_parse_jd_integration_realistic(monkeypatch, tmp_path):
    """Integration test with real OpenAI API - only runs if API key present."""
    from roleskills.jd.preprocess import clean_jd_text
    from roleskills.jd.parser import parse_jd as deterministic_parse

    # Use real realistic JD
    jd_text = (DATA / "jd_realistic.md").read_text()

    # Capture what gets sent to LLM
    cleaned = clean_jd_text(jd_text)
    deterministic = deterministic_parse(cleaned)

    print("\n" + "="*80)
    print("CLEANED TEXT SENT TO LLM:")
    print("="*80)
    print(cleaned[:2000])  # First 2000 chars
    print("...")
    print("="*80)

    print("\nDETERMINISTIC PRE-PARSE:")
    print("="*80)
    print(f"Requirements found: {len(deterministic.requirements)}")
    for req in deterministic.requirements[:5]:  # First 5
        print(f"  [{req.weight.value}] {req.title}")
    if len(deterministic.requirements) > 5:
        print(f"  ... and {len(deterministic.requirements) - 5} more")
    print("="*80)

    result = llm_parse_jd(jd_text)

    # Verify structure
    assert isinstance(result, JD)
    assert result.role is not None
    assert len(result.requirements) > 0

    # Verify reasonable weights
    weights = {r.weight.value for r in result.requirements}
    assert weights <= {"must", "strong", "nice"}

    # Verify tags are normalized (lowercase-with-dashes)
    for req in result.requirements:
        for tag in req.tags:
            assert tag.islower() or "-" in tag
            assert " " not in tag  # No spaces in tags

    print("\n✅ LLM REFINED RESULT:")
    print(f"   Role: {result.role}")
    print(f"   Requirements: {len(result.requirements)}")
    print("\n   Requirements by weight:")
    for weight in ["must", "strong", "nice"]:
        reqs = [r for r in result.requirements if r.weight.value == weight]
        print(f"     {weight}: {len(reqs)}")
        for req in reqs[:3]:  # Show first 3 of each weight
            print(f"       - {req.title} (tags: {', '.join(req.tags[:3])})")
        if len(reqs) > 3:
            print(f"       ... and {len(reqs) - 3} more")