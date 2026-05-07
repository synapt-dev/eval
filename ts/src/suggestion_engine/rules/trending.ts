import { SEVERITY_ERROR, SEVERITY_WARNING } from "../../reviewer/types.ts";
import type { SuggestionRule } from "../protocol.ts";
import type { Suggestion } from "../types.ts";
import type { EvalResult } from "../../types.ts";

type MetricKey = "pAt5" | "rAt10" | "tau" | "n";

export class MonotonicDegradationRule implements SuggestionRule {
  private readonly metric: MetricKey;
  private readonly consecutive: number;

  constructor(metric: MetricKey = "pAt5", consecutive = 3) {
    this.metric = metric;
    this.consecutive = consecutive;
  }

  evaluate(
    result: EvalResult,
    _verdicts?: unknown,
    context?: Record<string, unknown>,
  ): Suggestion[] {
    if (!context || !context["history"]) return [];

    const history = context["history"] as EvalResult[];
    const sameCategory = [
      ...history.filter((r) => r.category === result.category),
      result,
    ];

    if (sameCategory.length < this.consecutive) return [];

    const values = sameCategory
      .map((r) => r.metrics[this.metric])
      .filter((v): v is number => v != null);

    if (values.length < this.consecutive) return [];

    const tail = values.slice(-this.consecutive);
    const monotonicDown = tail.every(
      (v, i) => i === 0 || tail[i - 1] > v,
    );

    if (!monotonicDown) return [];

    const metricName = this.metricDisplayName();
    return [
      {
        severity: SEVERITY_ERROR,
        message: `${metricName} has degraded for ${this.consecutive} consecutive runs in category '${result.category}': ${tail.map((v) => v.toFixed(3)).join(" -> ")}`,
        ruleName: "monotonic_degradation",
        metric: metricName,
        category: result.category,
        fixHint:
          "Investigate recent changes; this metric is trending consistently downward.",
      },
    ];
  }

  private metricDisplayName(): string {
    const map: Record<MetricKey, string> = {
      pAt5: "p_at_5",
      rAt10: "r_at_10",
      tau: "tau",
      n: "n",
    };
    return map[this.metric];
  }
}

export class StableLowRule implements SuggestionRule {
  private readonly metric: MetricKey;
  private readonly threshold: number;
  private readonly minRuns: number;

  constructor(
    metric: MetricKey = "pAt5",
    threshold = 0.7,
    minRuns = 3,
  ) {
    this.metric = metric;
    this.threshold = threshold;
    this.minRuns = minRuns;
  }

  evaluate(
    result: EvalResult,
    _verdicts?: unknown,
    context?: Record<string, unknown>,
  ): Suggestion[] {
    if (!context || !context["history"]) return [];

    const history = context["history"] as EvalResult[];
    const sameCategory = [
      ...history.filter((r) => r.category === result.category),
      result,
    ];

    if (sameCategory.length < this.minRuns) return [];

    const values = sameCategory
      .map((r) => r.metrics[this.metric])
      .filter((v): v is number => v != null);

    if (values.length < this.minRuns) return [];

    const tail = values.slice(-this.minRuns);
    const allBelow = tail.every((v) => v < this.threshold);

    if (!allBelow) return [];

    const avg = tail.reduce((s, v) => s + v, 0) / tail.length;
    const metricName = this.metricDisplayName();
    return [
      {
        severity: SEVERITY_WARNING,
        message: `${metricName} has been below ${this.threshold.toFixed(2)} for ${this.minRuns} consecutive runs in category '${result.category}' (avg: ${avg.toFixed(3)})`,
        ruleName: "stable_low",
        metric: metricName,
        category: result.category,
        fixHint:
          "This metric is consistently underperforming; consider architectural changes rather than incremental tuning.",
      },
    ];
  }

  private metricDisplayName(): string {
    const map: Record<MetricKey, string> = {
      pAt5: "p_at_5",
      rAt10: "r_at_10",
      tau: "tau",
      n: "n",
    };
    return map[this.metric];
  }
}
