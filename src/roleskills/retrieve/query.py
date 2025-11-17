"""Convert JD requirements to search queries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Set

from ..jd.schema import Requirement, WEIGHT_NUM

# Common stopwords to filter out
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "will",
    "with",
}


@dataclass
class Query:
    """Search query representation for a requirement."""

    requirement_id: str
    terms: List[str]  # Tokenized words
    tags: List[str]  # Normalized skill tags
    weight: float  # Numeric weight (must=3, strong=2, nice=1)


def tokenize(text: str) -> List[str]:
    """
    Tokenize text into searchable words.

    Args:
        text: Input text

    Returns:
        List of lowercase tokens

    Example:
        >>> tokenize("Azure Functions & Logic Apps")
        ['azure', 'functions', 'logic', 'apps']
    """
    # Split on non-alphanumeric, lowercase
    tokens = re.findall(r"\b\w+\b", text.lower())

    # Filter stopwords and short tokens
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) >= 2]

    return tokens


def requirement_to_query(req: Requirement) -> Query:
    """
    Convert JD requirement to search query.

    Args:
        req: JD requirement

    Returns:
        Query object

    Example:
        >>> from roleskills.jd.schema import Requirement, Weight
        >>> req = Requirement(
        ...     id="abc",
        ...     title="Experience with Azure Functions",
        ...     weight=Weight.must,
        ...     tags=["azure", "functions"],
        ...     source_text="Azure Functions for serverless compute"
        ... )
        >>> q = requirement_to_query(req)
        >>> q.tags
        ['azure', 'functions']
        >>> 'serverless' in q.terms
        True
    """
    # Combine title and source text
    combined_text = f"{req.title} {req.source_text}"

    # Tokenize
    terms = tokenize(combined_text)

    # Remove duplicates while preserving order
    seen: Set[str] = set()
    unique_terms = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            unique_terms.append(term)

    return Query(
        requirement_id=req.id,
        terms=unique_terms,
        tags=req.tags,
        weight=WEIGHT_NUM[req.weight],
    )