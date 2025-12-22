"""LLM-enhanced JD parser with hybrid approach."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .preprocess import clean_jd_text
from .parser import parse_jd as deterministic_parse
from .schema import JD

CACHE_DIR = Path(".cache/jd_parsed")


def llm_parse_jd(text: str, model: str = "gpt-4o-mini", use_cache: bool = True) -> JD:
    """Hybrid JD parser: deterministic pre-parse + LLM refinement.

    Args:
        text: Raw JD text
        model: OpenAI model to use for refinement
        use_cache: Whether to use cached results

    Returns:
        Parsed and refined JD structure

    Raises:
        ValueError: If OPENAI_API_KEY not set
    """
    # Check for API key first
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "OPENAI_API_KEY environment variable not set.\n"
            "Please set it in your .env file or export OPENAI_API_KEY=your-key\n"
            "The LLM parser requires OpenAI API access for semantic enhancement."
        )

    # Clean and cache (SHA1 used for cache key, not security)
    cleaned = clean_jd_text(text)
    cache_key = hashlib.sha1(cleaned.encode(), usedforsecurity=False).hexdigest()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{cache_key}.json"

    if use_cache and cache_path.exists():
        return JD.model_validate_json(cache_path.read_text())

    # Import here to avoid requiring openai if not using LLM parser
    from openai import OpenAI

    client = OpenAI()

    # Run deterministic parse first
    deterministic = deterministic_parse(cleaned)

    # Build LLM prompt
    prompt = f"""You are an expert in analyzing job descriptions.

Given the pre-parsed requirements below, output corrected JSON matching this schema:

{{
  "role": "string (job title)",
  "title": "string or null",
  "requirements": [
    {{
      "id": "string (use same IDs from preparsed)",
      "title": "string (normalized, clear)",
      "weight": "must|strong|nice",
      "tags": ["skill-tag-1", "skill-tag-2"],
      "source_text": "string (original text)",
      "section": "string (section name)"
    }}
  ]
}}

Guidelines:
- Normalize skill tags to lowercase-with-dashes (e.g. 'Azure DevOps' → 'azure-devops')
- Merge duplicate requirements
- Infer missing weights from context:
  - "must", "required", "minimum" → must
  - "strong", "proven", "X+ years" → strong
  - "nice to have", "preferred", "bonus" → nice
- Keep all source_text and sections from preparsed data
- Ensure tags are consistent and canonical

---
TEXT (first 5000 chars):
{cleaned[:5000]}

---
PREPARSED:
{json.dumps(deterministic.model_dump(), indent=2)}

Output only valid JSON, no explanation."""

    # Call OpenAI
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,  # Low temperature for consistency
    )

    result_json = response.choices[0].message.content
    if result_json is None:
        raise ValueError("OpenAI returned empty response")
    jd = JD.model_validate_json(result_json)

    # Cache result
    cache_path.write_text(jd.model_dump_json(indent=2))

    return jd