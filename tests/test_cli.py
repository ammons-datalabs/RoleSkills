"""Tests for CLI."""

from roleskills.cli import main


def test_cli_ok(capsys):
    """CLI should run successfully with no args."""
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "roleskills: ok" in captured.out


def test_version(capsys):
    """CLI should print version."""
    rc = main(["--version"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "0.1.0" in captured.out