import type { Verdict } from "../reviewer/types.ts";
import type { EvalResult } from "../types.ts";
import type { SuggestionRule } from "./protocol.ts";
import type { Suggestion } from "./types.ts";
import { defaultRules } from "./rules/mod.ts";

export class SuggestionEngine {
  private readonly _rules: SuggestionRule[] = [];

  register(rule: SuggestionRule): void {
    this._rules.push(rule);
  }

  get rules(): SuggestionRule[] {
    return [...this._rules];
  }

  evaluate(
    result: EvalResult,
    verdicts?: Verdict[],
    context?: Record<string, unknown>,
  ): Suggestion[] {
    const suggestions: Suggestion[] = [];
    for (const rule of this._rules) {
      const categories = rule.categories;
      if (categories && !categories.has(result.category)) continue;
      suggestions.push(...rule.evaluate(result, verdicts, context));
    }
    suggestions.sort((a, b) => b.severity.weight - a.severity.weight);
    return suggestions;
  }

  evaluateAll(
    results: EvalResult[],
    verdicts?: Verdict[],
    context?: Record<string, unknown>,
  ): Suggestion[] {
    const suggestions: Suggestion[] = [];
    for (const result of results) {
      suggestions.push(...this.evaluate(result, verdicts, context));
    }
    suggestions.sort((a, b) => b.severity.weight - a.severity.weight);
    return suggestions;
  }

  static withDefaults(): SuggestionEngine {
    const engine = new SuggestionEngine();
    for (const rule of defaultRules()) {
      engine.register(rule);
    }
    return engine;
  }
}
