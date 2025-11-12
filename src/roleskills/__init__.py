"""RoleSkills - Extract and score role-specific skills from code and job descriptions."""

__version__ = "0.1.0"

from .observability import ObservabilityProvider, create_observability
from .config import configure_lm_from_env, log_langfuse_generation

__all__ = [
    "__version__",
    "ObservabilityProvider",
    "create_observability",
    "configure_lm_from_env",
    "log_langfuse_generation",
]
