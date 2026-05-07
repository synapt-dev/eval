import { SEVERITY_ERROR, SEVERITY_WARNING } from "../../reviewer/types.ts";
import type { SuggestionRule } from "../protocol.ts";
import type { Suggestion } from "../types.ts";
import type { EvalResult } from "../../types.ts";

export class LowPrecisionRule implements SuggestionRule {
  readonly categories = new Set(["retrieval"]);
  private readonly threshold: number;

  constructor(threshold = 0.7) {
    this.threshold = threshold;
  }

  evaluate(result: EvalResult): Suggestion[] {
    if (result.metrics.pAt5 >= this.threshold) return [];
    return [
      {
        severity: SEVERITY_WARNING,
        message: `P@5 is ${result.metrics.pAt5.toFixed(2)}, below threshold ${this.threshold.toFixed(2)}`,
        ruleName: "low_precision",
        metric: "p_at_5",
        category: result.category,
        fixHint:
          "Review retrieval ranking; consider re-embedding or tuning similarity thresholds.",
      },
    ];
  }
}

export class LowRecallRule implements SuggestionRule {
  readonly categories = new Set(["retrieval"]);
  private readonly threshold: number;

  constructor(threshold = 0.6) {
    this.threshold = threshold;
  }

  evaluate(result: EvalResult): Suggestion[] {
    if (result.metrics.rAt10 >= this.threshold) return [];
    return [
      {
        severity: SEVERITY_WARNING,
        message: `R@10 is ${result.metrics.rAt10.toFixed(2)}, below threshold ${this.threshold.toFixed(2)}`,
        ruleName: "low_recall",
        metric: "r_at_10",
        category: result.category,
        fixHint:
          "Relevant items are being missed; check chunk boundaries and embedding coverage.",
      },
    ];
  }
}

export class HighNoResultsRule implements SuggestionRule {
  readonly categories = new Set(["retrieval"]);
  private readonly threshold: number;

  constructor(threshold = 0.1) {
    this.threshold = threshold;
  }

  evaluate(result: EvalResult): Suggestion[] {
    const fixtures = result.perFixture ?? [];
    if (fixtures.length === 0) return [];

    const noResultCount = fixtures.filter((pf) => pf.score === 0).length;
    const rate = noResultCount / fixtures.length;

    if (rate <= this.threshold) return [];

    return [
      {
        severity: SEVERITY_ERROR,
        message: `${noResultCount}/${fixtures.length} fixtures (${Math.round(rate * 100)}%) returned no results`,
        ruleName: "high_no_results",
        metric: "no_results_rate",
        category: result.category,
        fixHint:
          "Check that queries match indexed content; verify embeddings are populated.",
      },
    ];
  }
}
