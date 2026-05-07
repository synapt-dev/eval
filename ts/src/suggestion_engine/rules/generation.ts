import { SEVERITY_ERROR, SEVERITY_WARNING } from "../../reviewer/types.ts";
import type { Verdict } from "../../reviewer/types.ts";
import type { SuggestionRule } from "../protocol.ts";
import type { Suggestion } from "../types.ts";
import type { EvalResult } from "../../types.ts";

export class LowSuccessRateRule implements SuggestionRule {
  readonly categories = new Set(["generation"]);
  private readonly threshold: number;

  constructor(threshold = 0.8) {
    this.threshold = threshold;
  }

  evaluate(result: EvalResult): Suggestion[] {
    if (result.metrics.pAt5 >= this.threshold) return [];
    return [
      {
        severity: SEVERITY_WARNING,
        message: `Generation success rate is ${Math.round(result.metrics.pAt5 * 100)}%, below threshold ${Math.round(this.threshold * 100)}%`,
        ruleName: "low_success_rate",
        metric: "success_rate",
        category: result.category,
        fixHint: "Check adapter error handling and API connectivity.",
      },
    ];
  }
}

export class HallucinationSignalRule implements SuggestionRule {
  readonly categories = new Set(["generation"]);
  private readonly scoreThreshold: number;

  constructor(scoreThreshold = 0.5) {
    this.scoreThreshold = scoreThreshold;
  }

  evaluate(
    result: EvalResult,
    verdicts?: Verdict[],
  ): Suggestion[] {
    if (!verdicts || verdicts.length === 0) return [];

    const flagged = verdicts.filter(
      (v) => !v.passed && v.score < this.scoreThreshold,
    );
    if (flagged.length === 0) return [];

    return [
      {
        severity: SEVERITY_ERROR,
        message: `${flagged.length} verdict(s) scored below ${this.scoreThreshold.toFixed(1)}, possible hallucination or fabricated content`,
        ruleName: "hallucination_signal",
        metric: "judge_score",
        category: result.category,
        fixHint:
          "Add grounding context to generation prompts; consider retrieval-augmented generation or stricter guardrails.",
      },
    ];
  }
}

export class VerdictFailureRule implements SuggestionRule {
  evaluate(
    result: EvalResult,
    verdicts?: Verdict[],
  ): Suggestion[] {
    if (!verdicts || verdicts.length === 0) return [];

    const suggestions: Suggestion[] = [];
    for (const verdict of verdicts) {
      for (const check of verdict.checks) {
        if (check.passed) continue;
        suggestions.push({
          severity: check.severity,
          message: `Check '${check.name}' failed: ${check.reasoning}`,
          ruleName: "verdict_failure",
          category: result.category,
        });
      }
    }
    return suggestions;
  }
}
