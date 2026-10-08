"""Round-trip a normalized collector record through the public result types."""

import json

import pytest

from synapt_eval import CategoryMetrics, EvalResult, RunCost, RunMetrics, TokenCount, TokenUsage
from synapt_eval.report_card import compose_report_card, generate_json, generate_markdown


def test_collector_to_result_round_trip():
    collector = {
        "runtime": "example-runtime",
        "runtime_versions": ["1.0"],
        "models": ["example-model"],
        "usage": {
            "prompt_tokens": {"value": 150, "status": "measured"},
            "cached_prompt_tokens": {"value": 100, "status": "measured"},
            "cache_write_tokens": {"value": None, "status": "unavailable"},
            "completion_tokens": {"value": 20, "status": "measured"},
            "total_tokens": {"value": 170, "status": "measured"},
        },
        "turns": 2,
        "tool_calls": 0,
        "wall_seconds": 10.5,
        "box_minutes": None,
        "model_cost": {"value_usd": 0.002, "status": "GUESS", "source": "example rates"},
        "box_cost": {"value_usd": None, "status": "unavailable"},
        "scope": "task window",
        "counting_rule": "unique events",
        "usage_basis": "provider counters",
        "wall_basis": "explicit task boundaries",
        "duplicate_records_removed": 1,
    }
    metrics = RunMetrics.from_collector(json.loads(json.dumps(collector)))
    result = EvalResult("workflow", CategoryMetrics(n=1), run_metrics=metrics)
    restored = EvalResult.from_dict(json.loads(json.dumps(result.to_dict())))
    assert restored == result
    assert restored.run_metrics.usage.cache_write_tokens.value is None
    assert restored.run_metrics.tool_calls == 0
    assert restored.run_metrics.model_cost.status == "GUESS"


def test_report_keeps_measurements_and_labels_without_summing():
    run = RunMetrics(
        usage=TokenUsage(prompt_tokens=TokenCount(0, "measured")),
        tool_calls=0,
        model_cost=RunCost(0.005, "GUESS", source="explicit rates"),
    )
    results = [EvalResult(key, CategoryMetrics(n=1), run_metrics=run) for key in ("a", "b")]
    card = compose_report_card(results)
    output = json.loads(json.dumps(generate_json(card)))
    assert output["schema_version"] == "1.1"
    for section in output["sections"]:
        assert RunMetrics.from_dict(section["run_metrics"]) == run
    assert "run_metrics" not in output["summary"]
    text = generate_markdown(card)
    assert "| prompt_tokens | 0 |" in text
    assert "| cache_write_tokens | unavailable |" in text
    assert "| Model cost USD | 0.005 (GUESS) |" in text


def test_legacy_result_round_trip_and_report():
    old = {"category": "old", "metrics": {"n": 1}, "per_fixture": []}
    result = EvalResult.from_dict(old)
    assert result.run_metrics is None
    card = compose_report_card([result])
    assert "run_metrics" not in generate_json(card)["sections"][0]
    assert "Run measurements" not in generate_markdown(card)


@pytest.mark.parametrize("value", [-1, True, 1.5, "1", float("nan")])
def test_token_count_rejects_bad_measurements(value):
    with pytest.raises(ValueError):
        TokenCount(value, "measured")


@pytest.mark.parametrize("value,status", [(None, "measured"), (0, "unavailable"), (1, "GUESS")])
def test_token_availability_is_consistent(value, status):
    with pytest.raises(ValueError):
        TokenCount(value, status)


@pytest.mark.parametrize(
    "field,value",
    [("tool_calls", -1), ("turns", True), ("wall_seconds", float("inf")), ("box_minutes", -0.1)],
)
def test_run_measurements_reject_invalid_values(field, value):
    with pytest.raises(ValueError):
        RunMetrics(**{field: value})


def test_cache_and_total_invariants():
    with pytest.raises(ValueError):
        TokenUsage(
            prompt_tokens=TokenCount(10, "measured"),
            cached_prompt_tokens=TokenCount(8, "measured"),
            cache_write_tokens=TokenCount(3, "measured"),
        )
    with pytest.raises(ValueError):
        TokenUsage(
            prompt_tokens=TokenCount(10, "measured"),
            completion_tokens=TokenCount(2, "measured"),
            total_tokens=TokenCount(13, "measured"),
        )


def test_reported_cost_and_sourced_estimate_round_trip():
    for cost in (
        RunCost(0, "measured", source="provider usage"),
        RunCost(0.01, "GUESS", rates={"source": "explicit rates", "input": 1}),
    ):
        assert (
            RunCost(**json.loads(json.dumps(RunMetrics(model_cost=cost).to_dict()))["model_cost"])
            == cost
        )
    with pytest.raises(ValueError):
        RunCost(0.1, "GUESS")
    with pytest.raises(ValueError):
        RunCost(float("nan"), "measured", source="provider")


def test_partial_collector_is_unavailable_not_zero():
    run = RunMetrics.from_collector({"runtime": "example", "warnings": ["not measured"]})
    assert run.usage.total_tokens.value is None
    assert run.turns is None and run.wall_seconds is None


def test_results_file_loader_keeps_run_measurements(tmp_path):
    from synapt_eval.actions.pr_gate import load_results

    run = RunMetrics(turns=1, model_cost=RunCost(0, "measured", source="provider usage"))
    original = EvalResult("workflow", CategoryMetrics(n=1), run_metrics=run)
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"results": [original.to_dict()]}))
    assert load_results(path) == [original]
