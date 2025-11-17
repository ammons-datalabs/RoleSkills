"""
Path filtering for evidence collection.
"""

import fnmatch
from pathlib import Path

# Default paths to include
DEFAULT_ALLOW = [
    "src/**",
    "tests/**",
    "docs/**",
    # CI/CD workflows
    ".github/workflows/**",
    ".github/actions/**",
    # Support .NET project structures (e.g., ProjectName.Api/*.cs)
    "**/*.cs",
    "**/*.csproj",
    # Support common project structures with code outside src/
    "**/*.go",
    "**/*.rs",
    "**/*.java",
    # Configuration files that show tech stack
    "**/*.yml",
    "**/*.yaml",
]

# Default paths to exclude (vendor code, build artifacts, binary files, etc.)
DEFAULT_DENY = [
    "vendor/**",
    "dist/**",
    "build/**",
    "node_modules/**",
    "**/*.lock",
    "**/*.min.js",
    "**/*.min.css",
    "**/.ipynb_checkpoints/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/*.png",
    "**/*.jpg",
    "**/*.jpeg",
    "**/*.gif",
    "**/*.ico",
    "**/*.svg",
    "**/*.woff",
    "**/*.woff2",
    "**/*.ttf",
    "**/*.eot",
]


def is_allowed(
    path: str,
    allow: list[str] | None = None,
    deny: list[str] | None = None,
) -> bool:
    """
    Check if a file path should be included in evidence collection.

    Args:
        path: File path to check
        allow: Glob patterns to allow (defaults to DEFAULT_ALLOW)
        deny: Glob patterns to deny (defaults to DEFAULT_DENY)

    Returns:
        True if path passes filters, False otherwise

    Rules:
        1. If path matches any deny pattern → reject
        2. If path matches any allow pattern → accept
        3. Otherwise → reject

    Example:
        >>> is_allowed("src/main.py")
        True
        >>> is_allowed("dist/bundle.js")
        False
        >>> is_allowed("vendor/lib.py")
        False
    """
    if allow is None:
        allow = DEFAULT_ALLOW
    if deny is None:
        deny = DEFAULT_DENY

    p = Path(path)

    # Check deny patterns first
    for pat in deny:
        if fnmatch.fnmatch(str(p), pat):
            return False

    # Check allow patterns
    for pat in allow:
        if fnmatch.fnmatch(str(p), pat):
            return True

    return False