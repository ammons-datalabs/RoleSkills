"""Tests for scoring rubric."""

from roleskills.jd.schema import JD, Requirement, Weight
from roleskills.score.factors import Factor
from roleskills.score.models import RequirementScore
from roleskills.score.rubric import score_requirement, overall_match


def test_score_requirement_full_coverage():
    """Test scoring with full coverage and high quality."""
    req = Requirement(
        id="test1",
        title="Python",
        weight=Weight.must,
        tags=["python"],
        source_text="Python programming",
    )

    factor = Factor(
        coverage=1.0,
        relevance=0.9,
        ownership=1.0,
        recency=1.0,
        quality=1.1,
    )

    score = score_requirement(req, factor)

    # weight=3 × 1.0 × 0.9 × 1.0 × 1.0 × 1.1 = 2.97
    assert score == 2.97


def test_score_requirement_no_coverage():
    """Test scoring with no coverage returns 0."""
    req = Requirement(
        id="test1",
        title="Python",
        weight=Weight.must,
        tags=["python"],
        source_text="",
    )

    factor = Factor(
        coverage=0.0,
        relevance=0.9,
        ownership=1.0,
        recency=1.0,
        quality=1.1,
    )

    score = score_requirement(req, factor)
    assert score == 0.0


def test_score_requirement_nice_weight():
    """Test scoring with nice weight (=1)."""
    req = Requirement(
        id="test1",
        title="Docker",
        weight=Weight.nice,
        tags=["docker"],
        source_text="",
    )

    factor = Factor(
        coverage=1.0,
        relevance=0.8,
        ownership=1.0,
        recency=0.5,
        quality=1.0,
    )

    score = score_requirement(req, factor)

    # weight=1 × 1.0 × 0.8 × 1.0 × 0.5 × 1.0 = 0.4
    assert score == 0.4


def test_overall_match_simple():
    """Test overall match calculation."""
    jd = JD(
        requirements=[
            Requirement(
                id="1", title="Python", weight=Weight.must, tags=[], source_text=""
            ),
            Requirement(
                id="2", title="Azure", weight=Weight.strong, tags=[], source_text=""
            ),
        ]
    )

    scores = [
        RequirementScore(
            id="1",
            title="Python",
            weight="must",
            score=2.7,
            coverage=1.0,
            relevance=0.9,
            ownership=1.0,
            recency=1.0,
            quality=1.0,
        ),
        RequirementScore(
            id="2",
            title="Azure",
            weight="strong",
            score=1.6,
            coverage=1.0,
            relevance=0.8,
            ownership=1.0,
            recency=1.0,
            quality=1.0,
        ),
    ]

    match = overall_match(jd, scores)

    # (2.7 + 1.6) / (3 + 2) = 4.3 / 5 = 0.86
    assert match == 0.86


def test_overall_match_empty_jd():
    """Test overall match with no requirements."""
    jd = JD(requirements=[])
    scores = []

    match = overall_match(jd, scores)
    assert match == 0.0


def test_overall_match_missing_scores():
    """Test overall match when some requirements have no score."""
    jd = JD(
        requirements=[
            Requirement(
                id="1", title="Python", weight=Weight.must, tags=[], source_text=""
            ),
            Requirement(
                id="2", title="Azure", weight=Weight.strong, tags=[], source_text=""
            ),
        ]
    )

    scores = [
        RequirementScore(
            id="1",
            title="Python",
            weight="must",
            score=3.0,
            coverage=1.0,
            relevance=1.0,
            ownership=1.0,
            recency=1.0,
            quality=1.0,
        ),
        # Missing score for requirement 2
    ]

    match = overall_match(jd, scores)

    # 3.0 / (3 + 2) = 3.0 / 5 = 0.6
    assert match == 0.6