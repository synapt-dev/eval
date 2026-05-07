import { SEVERITY_ERROR, SEVERITY_WARNING } from "../../reviewer/types.ts";
import type { SuggestionRule } from "../protocol.ts";
import type { Suggestion } from "../types.ts";
import type { EvalResult } from "../../types.ts";

export class RegressionRule implements SuggestionRule {
  private readonly threshold: number;

  constructor(regressionThreshold = 0.05) {
    this.threshold = regressionThreshold;
  }

  evaluate(
    result: EvalResult,
    _verdicts?: unknown,
    context?: Record<string, unknown>,
  ): Suggestion[] {
    if (!context || !context["baseline"]) return [];

    const baseline = context["baseline"] as EvalResult[];
    const baselineForCategory = baseline.find(
      (b) => b.category === result.category,
    );
    if (!baselineForCategory) return [];

    const suggestions: Suggestion[] = [];
    const metrics: Array<{ key: keyof EvalResult["metrics"]; name: string }> = [
      { key: "pAt5", name: "p_at_5" },
      { key: "rAt10", name: "r_at_10" },
    ];

    for (const { key, name } of metrics) {
      const current = result.metrics[key] as number;
      const base = baselineForCategory.metrics[key] as number;
      if (typeof current !== "number" || typeof base !== "number") continue;
      const delta = current - base;
      if (delta < -this.threshold) {
        suggestions.push({
          severity: SEVERITY_ERROR,
          message: `${name} regressed: ${base.toFixed(3)} -> ${current.toFixed(3)} (delta: ${delta >= 0 ? "+" : ""}${delta.toFixed(3)})`,
          ruleName: "regression",
          metric: name,
          category: result.category,
          fixHint:
            "Compare recent changes against the baseline run to identify the cause.",
        });
      }
    }
    return suggestions;
  }
}

export class CategoryImbalanceRule implements SuggestionRule {
  private readonly ratio: number;

  constructor(imbalanceRatio = 3.0) {
    this.ratio = imbalanceRatio;
  }

  evaluate(
    _result: EvalResult,
    _verdicts?: unknown,
    context?: Record<string, unknown>,
  ): Suggestion[] {
    if (!context || !context["all_results"]) return [];

    const allResults = context["all_results"] as EvalResult[];
    const counts = allResults
      .filter((r) => r.metrics.n > 0)
      .map((r) => r.metrics.n);

    if (counts.length < 2) return [];

    const maxN = Math.max(...counts);
    const minN = Math.min(...counts);

    if (minN === 0 || maxN / minN <= this.ratio) return [];

    return [
      {
        severity: SEVERITY_WARNING,
        message: `Category fixture counts are imbalanced: smallest=${minN}, largest=${maxN} (ratio ${(maxN / minN).toFixed(1)}x)`,
        ruleName: "category_imbalance",
        metric: "fixture_count",
        fixHint:
          "Add more fixtures to underrepresented categories for balanced evaluation.",
      },
    ];
  }
}
