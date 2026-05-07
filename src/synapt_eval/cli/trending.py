"""CLI trending subcommand: view eval history and metric deltas."""

from __future__ import annotations

import json
import sys
from argparse import Namespace, _SubParsersAction
from typing import Any

from synapt_eval.trending.store import TrendingStore, compute_trending_deltas

_ARROW_UP = "^"
_ARROW_DOWN = "v"
_ARROW_FLAT = "-"

_WORD_UP = "up"
_WORD_DOWN = "down"
_WORD_FLAT = "flat"


def add_trending_subcommand(subparsers: _SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the trending subcommand."""
    parser = subparsers.add_parser(
        "trending",
        help="View eval run history and metric trends",
    )
    parser.add_argument(
        "--path",
        default=".synapt-eval/history",
        help="Path to history directory (default: .synapt-eval/history)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of recent runs to show (default: 10)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        dest="output_format",
        help="Output format (default: text)",
    )
    parser.set_defaults(func=_run_trending)


def _run_trending(args: Namespace) -> int:
    """Execute the trending subcommand."""
    store = TrendingStore(args.path)
    history = store.load_history(limit=args.limit)

    if not history:
        print("No eval history found.", file=sys.stderr)
        return 1

    if args.output_format == "json":
        print(json.dumps(history, indent=2, default=str))
    elif args.output_format == "markdown":
        print(_format_markdown(history))
    else:
        use_arrows = sys.stdout.isatty()
        print(_format_text(history, use_arrows=use_arrows))

    return 0


def _format_text(
    history: list[dict[str, Any]],
    use_arrows: bool = True,
) -> str:
    """Format history as a text table with delta indicators."""
    deltas = compute_trending_deltas(history)
    delta_map: dict[tuple[str, str], dict[str, Any]] = {}
    for d in deltas:
        delta_map[(d["category"], d["metric"])] = d

    lines: list[str] = []
    lines.append("Eval Trending")
    lines.append("=" * 60)
    lines.append("")

    for run in history:
        run_id = run.get("run_id", "unknown")
        passed = run.get("passed", None)
        status = "PASS" if passed else "FAIL" if passed is not None else "?"
        lines.append(f"Run: {run_id}  Status: {status}")

        for section in run.get("sections", []):
            cat = section["category"]
            metrics = section.get("metrics", {})
            parts: list[str] = []
            for metric in ("p_at_5", "r_at_10", "tau"):
                val = metrics.get(metric)
                if val is None:
                    continue
                indicator = ""
                key = (cat, metric)
                if key in delta_map and run == history[0]:
                    direction = delta_map[key]["direction"]
                    indicator = _direction_indicator(direction, use_arrows)
                parts.append(f"{metric}={val:.3f}{indicator}")
            lines.append(f"  {cat}: {', '.join(parts)}")

        lines.append("")

    return "\n".join(lines).rstrip()


def _format_markdown(history: list[dict[str, Any]]) -> str:
    """Format history as markdown tables."""
    lines: list[str] = []
    lines.append("# Eval Trending")
    lines.append("")

    categories: set[str] = set()
    for run in history:
        for section in run.get("sections", []):
            categories.add(section["category"])

    for category in sorted(categories):
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| Run | P@5 | R@10 | Tau | Status |")
        lines.append("|-----|-----|------|-----|--------|")

        for run in history:
            run_id = run.get("run_id", "?")
            passed = run.get("passed")
            status = "PASS" if passed else "FAIL" if passed is not None else "?"
            section = _find_section(run, category)
            if section is None:
                continue
            metrics = section.get("metrics", {})
            p5 = metrics.get("p_at_5")
            r10 = metrics.get("r_at_10")
            tau = metrics.get("tau")
            p5_str = f"{p5:.3f}" if p5 is not None else "-"
            r10_str = f"{r10:.3f}" if r10 is not None else "-"
            tau_str = f"{tau:.3f}" if tau is not None else "-"
            lines.append(f"| {run_id} | {p5_str} | {r10_str} | {tau_str} | {status} |")

        lines.append("")

    return "\n".join(lines).rstrip()


def _find_section(run: dict[str, Any], category: str) -> dict[str, Any] | None:
    for section in run.get("sections", []):
        if section["category"] == category:
            return section
    return None


def _direction_indicator(direction: str, use_arrows: bool) -> str:
    if use_arrows:
        return {
            "up": _ARROW_UP,
            "down": _ARROW_DOWN,
            "flat": _ARROW_FLAT,
        }.get(direction, "")
    return {
        "up": f"({_WORD_UP})",
        "down": f"({_WORD_DOWN})",
        "flat": f"({_WORD_FLAT})",
    }.get(direction, "")
