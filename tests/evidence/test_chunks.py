"""Tests for diff parsing and chunking."""


from roleskills.evidence.chunks import iter_diff_hunks, normalize_text


def test_iter_diff_hunks_basic():
    """Test basic diff hunk extraction."""
    patch = """
diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -10,3 +10,4 @@
 def foo():
+    bar()
     pass
"""
    hunks = list(iter_diff_hunks(patch))
    assert len(hunks) == 1

    path, start, end, text = hunks[0]
    assert path == "src/main.py"
    assert start == 10
    assert "def foo():" in text
    assert "+    bar()" in text


def test_iter_diff_hunks_multiple():
    """Test multiple hunks in one file."""
    patch = """
diff --git a/src/api.py b/src/api.py
--- a/src/api.py
+++ b/src/api.py
@@ -5,2 +5,3 @@
 def get():
+    # New comment
     return {}
@@ -20,1 +21,2 @@
 def post():
+    validate()
     return {}
"""
    hunks = list(iter_diff_hunks(patch))
    assert len(hunks) == 2

    # First hunk
    path1, start1, end1, text1 = hunks[0]
    assert path1 == "src/api.py"
    assert start1 == 5
    assert "# New comment" in text1

    # Second hunk
    path2, start2, end2, text2 = hunks[1]
    assert path2 == "src/api.py"
    assert start2 == 21
    assert "validate()" in text2


def test_iter_diff_hunks_multiple_files():
    """Test hunks across multiple files."""
    patch = """
diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,1 +1,2 @@
 x = 1
+y = 2
diff --git a/src/b.py b/src/b.py
--- a/src/b.py
+++ b/src/b.py
@@ -1,1 +1,2 @@
 a = 1
+b = 2
"""
    hunks = list(iter_diff_hunks(patch))
    assert len(hunks) == 2

    path1, _, _, text1 = hunks[0]
    assert path1 == "src/a.py"
    assert "y = 2" in text1

    path2, _, _, text2 = hunks[1]
    assert path2 == "src/b.py"
    assert "b = 2" in text2


def test_iter_diff_hunks_max_lines():
    """Test that hunks respect max_lines limit."""
    # Create a patch with many lines
    lines = ["@@ -1,1 +1,100 @@"]
    for i in range(60):
        lines.append(f"+line {i}")

    patch = f"""
diff --git a/src/big.py b/src/big.py
--- a/src/big.py
+++ b/src/big.py
{chr(10).join(lines)}
"""
    hunks = list(iter_diff_hunks(patch, max_lines=40))
    assert len(hunks) == 1

    _, _, _, text = hunks[0]
    # Should be truncated to 40 lines
    assert text.count("\n") <= 40


def test_normalize_text():
    """Test text normalization."""
    text = """
+    def foo():
+        bar()
     pass
"""
    normalized = normalize_text(text)
    assert normalized == "def foo(): bar() pass"


def test_normalize_text_removes_diff_markers():
    """Test that normalization removes diff markers."""
    text = "+added line\n-removed line\n context line"
    normalized = normalize_text(text)
    assert "+" not in normalized
    assert "-" not in normalized
    assert "added line" in normalized
    assert "removed line" in normalized
    assert "context line" in normalized


def test_normalize_text_collapses_whitespace():
    """Test that normalization collapses whitespace."""
    text = "  foo   bar  \n  baz  "
    normalized = normalize_text(text)
    assert normalized == "foo bar baz"