"""
Evidence indexing package for RoleSkills.

M3a: Builds deterministic evidence index from GitHub commits with zero LLM cost.
"""

from .schema import EvidenceChunk
from .store import EvidenceStore
from .builder import build_index

__all__ = ["EvidenceChunk", "EvidenceStore", "build_index"]