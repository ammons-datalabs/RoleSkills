"""RoleSkills CLI (M0 skeleton)."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .observability import create_observability


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="roleskills", description="RoleSkills - Extract and score role-specific skills"
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    # M0: no real commands yet, just a traced no-op
    observability = create_observability("cli", configure_lm=False)
    observability.logger.info("RoleSkills CLI (M0 skeleton)")
    print("roleskills: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
