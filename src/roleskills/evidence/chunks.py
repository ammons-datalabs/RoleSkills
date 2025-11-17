"""
Diff parsing and hunk extraction for evidence chunking.
"""

import re
from typing import Iterator

# Pattern to match unified diff hunk headers
# Example: @@ -10,5 +12,7 @@
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<len>\d+))? @@")


def iter_diff_hunks(
    patch: str, max_lines: int = 40
) -> Iterator[tuple[str, int, int, str]]:
    """
    Parse unified diff and yield (path, start_line, end_line, text) for each hunk.

    Args:
        patch: Unified diff output from git show/diff
        max_lines: Maximum lines per hunk (default 40)

    Yields:
        Tuple of (file_path, start_line, end_line, hunk_text)

    Example:
        >>> patch = '''
        ... diff --git a/src/main.py b/src/main.py
        ... --- a/src/main.py
        ... +++ b/src/main.py
        ... @@ -10,3 +10,4 @@
        ...  def foo():
        ... +    bar()
        ...      pass
        ... '''
        >>> list(iter_diff_hunks(patch))
        [('src/main.py', 10, 13, 'def foo():\\n+    bar()\\n    pass')]
    """
    path = None
    lines = patch.splitlines()
    i = 0

    while i < len(lines):
        ln = lines[i]

        # Track current file
        if ln.startswith("+++ b/"):
            path = ln[6:]

        # Look for hunk header
        m = HUNK_HEADER.match(ln)
        if m and path:
            start = int(m.group("start"))
            length = int(m.group("len") or "1")

            # Collect hunk lines (lines starting with +, -, or space)
            buf = []
            j = i + 1
            while j < len(lines) and lines[j].startswith(("+", "-", " ")):
                # Keep additions and context, skip pure deletions for now
                if not lines[j].startswith("-"):
                    buf.append(lines[j])
                j += 1

            # Truncate to max_lines
            if len(buf) > max_lines:
                buf = buf[:max_lines]

            # Calculate end line
            # Count actual added/kept lines (not deletions)
            added_lines = sum(1 for line in buf if line.startswith(("+", " ")))
            end = start + max(1, added_lines) - 1

            # Join and yield
            body = "\n".join(buf)
            if body.strip():  # Only yield non-empty hunks
                yield (path, start, end, body)

            i = j
            continue

        i += 1


def normalize_text(text: str) -> str:
    """
    Normalize text for de-duplication.

    Args:
        text: Raw text from diff hunk

    Returns:
        Normalized text (whitespace collapsed, trimmed)

    Example:
        >>> normalize_text("  foo   bar  \\n  baz  ")
        'foo bar baz'
    """
    # Remove leading diff markers (+, -, space)
    lines = []
    for line in text.splitlines():
        if line and line[0] in ("+", "-", " "):
            lines.append(line[1:])
        else:
            lines.append(line)

    # Join lines and split on whitespace to collapse all spaces
    # This handles both intra-line and inter-line whitespace
    normalized = " ".join(" ".join(line.split()) for line in lines if line.strip())
    return normalized