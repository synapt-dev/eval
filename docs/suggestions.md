# Suggestion Engine

The suggestion engine produces actionable recommendations from eval results. It ships with 10 baseline rules and supports custom rules via class or decorator.

## Built-in rules

### Retrieval rules

| Rule | Threshold | Fires when |
|------|-----------|------------|
| `LowPrecisionRule` | P@5 < 0.7 | Precision below threshold |
| `LowRecallRule` | R@10 < 0.6 | Recall below threshold |
| `HighNoResultsRule` | > 10% | Too many empty result sets |

### Generation rules

| Rule | Threshold | Fires when |
|------|-----------|------------|
| `LowSuccessRateRule` | < 80% | Too many generation failures |
| `HallucinationSignalRule` | > 50% | Judge flagging hallucinations |
| `VerdictFailureRule` | any | Any reviewer verdict failed |

### Cross-cutting rules

| Rule | Threshold | Fires when |
|------|-----------|------------|
| `RegressionRule` | delta > 5% | Metric dropped vs. baseline |
| `CategoryImbalanceRule` | ratio > 3x | Wide gap between best/worst category |

### Trending rules

| Rule | Condition | Fires when |
|------|-----------|------------|
| `MonotonicDegradationRule` | 3 runs | P@5 declining for N consecutive runs |
| `StableLowRule` | 3 runs | P@5 below threshold for N runs |

## Using the engine

```python
from synapt_eval.suggestion_engine import SuggestionEngine

# Create with all 10 baseline rules
engine = SuggestionEngine.with_defaults()

# Evaluate a single category
suggestions = engine.evaluate(result, context={"baseline": baseline_result})

# Evaluate all categories at once
suggestions = engine.evaluate_all(results, context={"history": history_results})
```

## Writing custom rules (class)

Implement the `SuggestionRule` protocol:

```python
from synapt_eval.suggestion_engine import SuggestionRule, Suggestion
from synapt_eval.reviewer.types import SEVERITY_WARNING
from synapt_eval import EvalResult


class SlowLatencyRule:
    name = "slow_latency"

    def evaluate(self, result: EvalResult, context: dict | None = None) -> list[Suggestion]:
        avg_latency = result.metrics.__dict__.get("avg_latency_ms", 0)
        if avg_latency > 500:
            return [Suggestion(
                severity=SEVERITY_WARNING,
                message=f"Average latency {avg_latency:.0f}ms exceeds 500ms target",
                rule_name=self.name,
                metric="avg_latency_ms",
                category=result.category,
                fix_hint="Check embedding model size or add caching",
            )]
        return []
```

## Writing custom rules (decorator)

For simple rules, use the `@suggestion_rule` decorator:

```python
from synapt_eval.suggestion_engine import suggestion_rule, Suggestion
from synapt_eval.reviewer.types import SEVERITY_INFO


@suggestion_rule("small_sample")
def small_sample_rule(result, context=None):
    if result.metrics.n < 10:
        return [Suggestion(
            severity=SEVERITY_INFO,
            message=f"Only {result.metrics.n} fixtures; results may not be statistically significant",
            rule_name="small_sample",
            metric="n",
            category=result.category,
            fix_hint="Add more fixtures to improve confidence",
        )]
    return []
```

## Registering custom rules

```python
engine = SuggestionEngine.with_defaults()

# Register class-based rule
engine.register(SlowLatencyRule())

# Register decorator-based rule
engine.register(small_sample_rule)
```

## Context dict

Rules can access shared context for cross-run analysis:

| Key | Type | Description |
|-----|------|-------------|
| `baseline` | `EvalResult` | Previous run for regression detection |
| `history` | `list[EvalResult]` | Historical runs for trending rules |

```python
suggestions = engine.evaluate_all(
    results,
    context={
        "baseline": previous_results,
        "history": last_5_runs,
    },
)
```
