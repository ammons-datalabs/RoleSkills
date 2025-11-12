"""JD text preprocessing and cleanup."""

from __future__ import annotations

import re


def clean_jd_text(raw: str) -> str:
    """Strip HTML, normalize whitespace, and drop irrelevant footer noise.

    Args:
        raw: Raw JD text, possibly with HTML tags and footer noise

    Returns:
        Cleaned text suitable for parsing
    """
    text = raw

    # Try to parse HTML if it looks like HTML
    if "<" in text and ">" in text:
        try:
            from bs4 import BeautifulSoup
            text = BeautifulSoup(text, "html.parser").get_text(" ")
        except ImportError:
            # beautifulsoup4 not installed, do basic tag stripping
            text = re.sub(r"<[^>]+>", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)  # Keep paragraph breaks

    # Remove typical footer clutter (split and take first part)
    for cutoff in [
        "Privacy Policy",
        "Terms of Service",
        "Terms and Conditions",
        "LinkedIn Corporation",
        "Apply Now",
        "© Copyright",
        "All rights reserved",
    ]:
        if cutoff in text:
            text = text.split(cutoff)[0]
            break

    return text.strip()
