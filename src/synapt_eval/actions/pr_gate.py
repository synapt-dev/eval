"""PR-gate GitHub Actions entrypoint.

Reads eval results JSON, runs regression gate, generates report card,
posts/updates a sticky PR comment, and sets action outputs.

Invoked via: python -m synapt_eval.actions.pr_gate
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from synapt_eval.report_card import compose_report_card, generate_json, generate_markdown
from synapt_eval.runner.orchestration import GateResult, load_baseline, pr_gate
from synapt_eval.trending.store import TrendingStore
from synapt_eval.types import CategoryMetrics, EvalResult, PerFixtureResult

COMMENT_MARKER = "<!-- synapt-eval-report -->"


@dataclass
class ActionInputs:
    """Parsed action inputs from environment variables."""

    results_path: str
    baseline_path: str | None
    threshold: float
    fail_on: str
    comment: bool
    trending_path: str | None


def parse_inputs() -> ActionInputs:
    """Parse GitHub Actions inputs from INPUT_* environment variables."""
    results_path = os.environ.get("INPUT_RESULTS-PATH", os.environ.get("INPUT_RESULTS_PATH", ""))
    if not results_path:
        _fail("Missing required input: results-path")

    baseline_path = os.environ.get("INPUT_BASELINE-PATH", os.environ.get("INPUT_BASELINE_PATH"))
    if baseline_path == "":
        baseline_path = None

    threshold_str = os.environ.get("INPUT_THRESHOLD", "0.05")
    try:
        threshold = float(threshold_str)
    except ValueError:
        _fail(f"Invalid threshold value: {threshold_str}")

    fail_on = os.environ.get("INPUT_FAIL-ON", os.environ.get("INPUT_FAIL_ON", "error"))
    if fail_on not in ("error", "warning", "none"):
        _fail(f"Invalid fail-on value: {fail_on}. Must be error, warning, or none.")

    comment_str = os.environ.get("INPUT_COMMENT", "true")
    comment = comment_str.lower() in ("true", "1", "yes")

    trending_path = os.environ.get("INPUT_TRENDING-PATH", os.environ.get("INPUT_TRENDING_PATH"))
    if trending_path == "":
        trending_path = None

    return ActionInputs(
        results_path=results_path,
        baseline_path=baseline_path,
        threshold=threshold,
        fail_on=fail_on,
        comment=comment,
        trending_path=trending_path,
    )


def load_results(path: str) -> list[EvalResult]:
    """Load eval results from a JSON file."""
    file_path = Path(path)
    if not file_path.exists():
        _fail(f"Results file not found: {path}")

    raw = json.loads(file_path.read_text(encoding="utf-8"))

    if isinstance(raw, dict):
        results_raw = raw.get("results", [])
    elif isinstance(raw, list):
        results_raw = raw
    else:
        _fail(f"Unexpected results format in {path}")

    results: list[EvalResult] = []
    for r in results_raw:
        metrics_raw = r.get("metrics", {})
        metrics = CategoryMetrics(
            p_at_5=metrics_raw.get("p_at_5", 0.0),
            r_at_10=metrics_raw.get("r_at_10", 0.0),
            tau=metrics_raw.get("tau"),
            n=metrics_raw.get("n", 0),
        )
        per_fixture = [
            PerFixtureResult(
                fixture_id=pf["fixture_id"],
                category=pf["category"],
                passed=pf["passed"],
                score=pf.get("score", 0.0),
                details=pf.get("details", {}),
            )
            for pf in r.get("per_fixture", [])
        ]
        results.append(
            EvalResult(
                category=r["category"],
                metrics=metrics,
                per_fixture=per_fixture,
            )
        )

    return results


def determine_passed(
    gate_result: GateResult,
    report_json: dict[str, Any],
    fail_on: str,
) -> bool:
    """Determine if the action should pass based on gate result and fail-on level.

    Regressions always fail regardless of fail-on level.
    """
    if not gate_result.passed:
        return False

    if fail_on == "none":
        return True

    error_count = report_json.get("summary", {}).get("error_count", 0)
    warning_count = report_json.get("summary", {}).get("warning_count", 0)

    if fail_on == "warning":
        return error_count == 0 and warning_count == 0

    return error_count == 0


def build_comment_body(markdown: str) -> str:
    """Build the PR comment body with sticky marker."""
    return f"{COMMENT_MARKER}\n{markdown}"


def post_or_update_comment(body: str) -> bool:
    """Post or update the sticky PR comment via gh CLI.

    Returns True if comment was posted/updated, False if not in a PR context.
    """
    pr_number = _get_pr_number()
    if not pr_number:
        return False

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        return False

    existing_id = _find_existing_comment(repo, pr_number)
    if existing_id:
        _update_comment(repo, existing_id, body)
    else:
        _create_comment(repo, pr_number, body)

    return True


def set_output(name: str, value: str) -> None:
    """Write a value to $GITHUB_OUTPUT."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return

    with open(output_file, "a", encoding="utf-8") as f:
        if "\n" in value:
            import uuid

            delimiter = f"ghadelimiter_{uuid.uuid4()}"
            f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
        else:
            f.write(f"{name}={value}\n")


def run_action(inputs: ActionInputs) -> int:
    """Execute the PR-gate action. Returns exit code."""
    results = load_results(inputs.results_path)

    baseline = None
    if inputs.baseline_path:
        baseline = load_baseline(inputs.baseline_path)

    gate_result = pr_gate(
        current=results,
        baseline=baseline or [],
        regression_threshold=inputs.threshold,
    )

    commit = os.environ.get("GITHUB_SHA")
    report_card = compose_report_card(
        results=results,
        baseline=baseline,
        commit=commit,
    )

    report_json = generate_json(report_card)
    markdown = generate_markdown(report_card)

    if inputs.trending_path:
        store = TrendingStore(inputs.trending_path)
        store.save(report_card)

    passed = determine_passed(gate_result, report_json, inputs.fail_on)

    report_json_path = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "synapt-eval-report.json"
    report_json_path.write_text(json.dumps(report_json, indent=2, default=str), encoding="utf-8")

    set_output("passed", str(passed).lower())
    set_output("report-json", str(report_json_path))
    set_output("report-markdown", markdown)

    if inputs.comment:
        comment_body = build_comment_body(markdown)
        posted = post_or_update_comment(comment_body)
        if not posted:
            print("Not in a PR context; skipping comment.", file=sys.stderr)

    print(gate_result.summary)

    if passed:
        print("PR gate: PASSED")
    else:
        print("PR gate: FAILED", file=sys.stderr)

    return 0 if passed else 1


def _fail(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    sys.exit(1)


def _get_pr_number() -> str | None:
    """Extract PR number from GitHub event context."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return None

    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        pr = event.get("pull_request", {})
        number = pr.get("number")
        return str(number) if number else None
    except (json.JSONDecodeError, KeyError):
        return None


def _find_existing_comment(repo: str, pr_number: str) -> str | None:
    """Find an existing synapt-eval comment on the PR."""
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/issues/{pr_number}/comments",
                "--jq",
                f'[.[] | select(.body | contains("{COMMENT_MARKER}"))][0].id',
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        comment_id = result.stdout.strip()
        return comment_id if comment_id and comment_id != "null" else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _update_comment(repo: str, comment_id: str, body: str) -> None:
    """Update an existing PR comment."""
    try:
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/issues/comments/{comment_id}",
                "-X",
                "PATCH",
                "-f",
                f"body={body}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("Warning: failed to update PR comment.", file=sys.stderr)


def _create_comment(repo: str, pr_number: str, body: str) -> None:
    """Create a new PR comment."""
    try:
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/issues/{pr_number}/comments",
                "-f",
                f"body={body}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("Warning: failed to create PR comment.", file=sys.stderr)


if __name__ == "__main__":
    inputs = parse_inputs()
    sys.exit(run_action(inputs))
