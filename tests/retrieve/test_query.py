"""Tests for query builder."""

from roleskills.jd.schema import Requirement, Weight
from roleskills.retrieve.query import tokenize, requirement_to_query


def test_tokenize_basic():
    """Test basic tokenization."""
    tokens = tokenize("Azure Functions & Logic Apps")

    assert "azure" in tokens
    assert "functions" in tokens
    assert "logic" in tokens
    assert "apps" in tokens
    # Stopwords removed
    assert "and" not in tokens


def test_tokenize_stopwords():
    """Test stopword filtering."""
    tokens = tokenize("The quick brown fox is jumping")

    assert "quick" in tokens
    assert "brown" in tokens
    assert "fox" in tokens
    assert "jumping" in tokens
    # Stopwords removed
    assert "the" not in tokens
    assert "is" not in tokens


def test_tokenize_special_chars():
    """Test handling of special characters."""
    tokens = tokenize("C# .NET developer (ASP.NET)")

    assert "net" in tokens
    assert "developer" in tokens
    assert "asp" in tokens


def test_requirement_to_query_basic():
    """Test query generation from requirement."""
    req = Requirement(
        id="req1",
        title="Experience with Azure Functions",
        weight=Weight.must,
        tags=["azure", "functions"],
        source_text="Azure Functions for serverless compute",
    )

    query = requirement_to_query(req)

    assert query.requirement_id == "req1"
    assert "azure" in query.tags
    assert "functions" in query.tags
    assert "serverless" in query.terms
    assert "compute" in query.terms
    assert query.weight == 3.0  # must = 3


def test_requirement_to_query_strong_weight():
    """Test query with strong weight."""
    req = Requirement(
        id="req2",
        title="Docker",
        weight=Weight.strong,
        tags=["docker"],
        source_text="Container orchestration",
    )

    query = requirement_to_query(req)

    assert query.weight == 2.0  # strong = 2


def test_requirement_to_query_deduplication():
    """Test that duplicate terms are removed."""
    req = Requirement(
        id="req3",
        title="Python Python development",
        weight=Weight.must,
        tags=["python"],
        source_text="Python programming in Python",
    )

    query = requirement_to_query(req)

    # Should only have "python" once in terms
    python_count = query.terms.count("python")
    assert python_count <= 1