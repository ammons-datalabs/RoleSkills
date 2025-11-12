"""Job Description parsing and schema."""

from .schema import JD, Requirement, Weight, WEIGHT_NUM
from .parser import parse_jd

__all__ = ["JD", "Requirement", "Weight", "WEIGHT_NUM", "parse_jd"]