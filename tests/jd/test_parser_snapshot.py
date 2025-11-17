"""Snapshot tests for JD parser."""

from __future__ import annotations

from pathlib import Path

from roleskills.jd.parser import parse_jd
from roleskills.jd.schema import WEIGHT_NUM

DATA = Path(__file__).parents[1] / "data"


def _stable(jd_obj):
    """Ensure deterministic ordering for snapshot."""
    jd = jd_obj.model_dump()
    jd["requirements"] = sorted(
        jd["requirements"],
        key=lambda r: (r.get("section", ""), -WEIGHT_NUM[r["weight"]], r["title"].lower()),
    )
    for r in jd["requirements"]:
        r["tags"] = sorted(set(r.get("tags", [])))
    return jd


def test_jd1_snapshot():
    """Test jd1.md parsing with full snapshot validation."""
    jd_text = (DATA / "jd1.md").read_text(encoding="utf-8")
    jd = parse_jd(jd_text, role="Senior Python Engineer")
    snap = _stable(jd)
    approved = {
        "role": "Senior Python Engineer",
        "title": None,
        "requirements": [
            {
                "id": snap["requirements"][0]["id"],  # id is deterministic but we don't pin hash
                "title": "Python, FastAPI, and experience with Azure",
                "weight": "must",
                "tags": ["azure", "fastapi", "python"],
                "source_text": "Must have: Python, FastAPI, and experience with Azure.",
                "section": "requirements",
            },
            {
                "id": snap["requirements"][1]["id"],
                "title": "Experience with Docker and GitHub Actions",
                "weight": "strong",
                "tags": ["docker", "github-actions"],
                "source_text": "Strong experience with Docker and GitHub Actions.",
                "section": "requirements",
            },
            {
                "id": snap["requirements"][2]["id"],
                "title": "Familiarity with SQL and Postgres",
                "weight": "nice",
                "tags": ["postgres", "sql"],
                "source_text": "Preferred: familiarity with SQL and Postgres.",
                "section": "requirements",
            },
        ],
    }
    # compare shapes/weights/tags; allow id variance by substituting computed ids
    assert len(snap["requirements"]) == 3
    # Replace ids before comparing
    for i in range(3):
        approved["requirements"][i]["id"] = snap["requirements"][i]["id"]
    assert snap == approved


def test_jd2_has_logicapps_and_servicebus():
    """Test jd2.md for integration-specific tags."""
    jd = parse_jd((DATA / "jd2.md").read_text(encoding="utf-8"))
    assert any("Logic Apps" in r.source_text for r in jd.requirements)
    assert any("Service Bus" in r.source_text for r in jd.requirements)
    tags = set().union(*[set(r.tags) for r in jd.requirements])
    assert {"logic-apps", "service-bus", "apim", "event-grid"} <= tags


def test_jd3_weights_and_tags():
    """Test jd3.md weight inference and tag detection."""
    jd = parse_jd((DATA / "jd3.md").read_text(encoding="utf-8"))
    by_title = {r.title.lower(): r for r in jd.requirements}
    assert by_title["strong python and pandas/numpy for etl"].weight.value == "must"
    assert {"python", "pandas", "numpy"} <= set(
        by_title["strong python and pandas/numpy for etl"].tags
    )
    # coverage/pytest cues end up strong by default
    assert "pytest" in by_title[
        "experience building tests with pytest; code coverage targets"
    ].tags
    # bonus → nice
    assert by_title["gcp or aws"].weight.value == "nice"


def test_realistic_jd_parsing():
    """Test realistic JD with multiple sections and nested bullets."""
    jd = parse_jd((DATA / "jd_realistic.md").read_text(encoding="utf-8"))

    # Should extract requirements from multiple sections
    assert len(jd.requirements) > 10, f"Expected >10 requirements, got {len(jd.requirements)}"

    # Check sections are parsed
    sections = {r.section for r in jd.requirements}
    assert "this role will" in sections or "to be successful in this role you will be able to demonstrate" in sections or "requirements" in sections

    # Check key Azure integration tags are detected
    all_tags = set()
    for r in jd.requirements:
        all_tags.update(r.tags)

    # Should detect various integration-related tags
    expected_tags = {"azure", "python", "javascript", "logic-apps", "service-bus", "apim"}
    found = expected_tags & all_tags
    assert len(found) >= 4, f"Expected at least 4 integration tags, found: {found}"

    # Check requirements have reasonable weights
    by_title_lower = {r.title.lower(): r for r in jd.requirements}

    # "Must have" requirement should be weighted appropriately
    if "must have the right to work in australia" in by_title_lower:
        assert by_title_lower["must have the right to work in australia"].weight.value == "must"

    # Check that we're extracting nested bullets (technologies list)
    tech_reqs = [r for r in jd.requirements if any(tag in r.tags for tag in ["python", "javascript", "azure"])]
    assert len(tech_reqs) >= 3, f"Expected at least 3 tech requirements, got {len(tech_reqs)}"