"""JD schema and data models."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Weight(str, Enum):
    """Requirement weight levels."""

    must = "must"  # weight=3
    strong = "strong"  # weight=2
    nice = "nice"  # weight=1


WEIGHT_NUM = {Weight.must: 3, Weight.strong: 2, Weight.nice: 1}


class Requirement(BaseModel):
    """A single requirement from a job description."""

    id: str
    title: str
    weight: Weight
    tags: List[str] = Field(default_factory=list)
    source_text: str  # original bullet/line
    section: Optional[str] = None


class JD(BaseModel):
    """Job description with parsed requirements."""

    role: Optional[str] = None
    title: Optional[str] = None
    requirements: List[Requirement] = Field(default_factory=list)