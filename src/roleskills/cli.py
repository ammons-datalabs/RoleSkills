"""RoleSkills CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .observability import create_observability


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="roleskills", description="RoleSkills - Extract and score role-specific skills"
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    # Add subcommands
    sub = parser.add_subparsers(dest="cmd")

    p_parse = sub.add_parser("jd-parse", help="Parse a JD markdown file to JSON")
    p_parse.add_argument("path", help="Path to JD .md/.txt")

    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.cmd == "jd-parse":
        text = Path(args.path).read_text(encoding="utf-8")
        from .jd.parser import parse_jd

        jd = parse_jd(text)
        print(json.dumps(jd.model_dump(), indent=2, ensure_ascii=False))
        return 0

    # Default behavior (no subcommand)
    observability = create_observability("cli", configure_lm=False)
    observability.logger.info("RoleSkills CLI")
    print("roleskills: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
