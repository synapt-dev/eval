"""synapt-eval CLI: argparse-based entry point with subcommands."""

from __future__ import annotations

import argparse
import sys

from synapt_eval.cli.trending import add_trending_subcommand


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="synapt-eval",
        description="synapt-eval: domain-agnostic eval framework for AI applications",
    )
    subparsers = parser.add_subparsers(dest="command")

    add_trending_subcommand(subparsers)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


def cli_entry() -> None:
    """Entry point for [project.scripts]."""
    sys.exit(main())
