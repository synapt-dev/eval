"""Round-trip a normalized collector record through the public result types."""

import json

from synapt_eval import CategoryMetrics, EvalResult, RunMetrics


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
