import type { Verdict } from "../reviewer/types.ts";
import type { EvalResult } from "../types.ts";
import type { Suggestion } from "./types.ts";

export interface SuggestionRule {
  categories?: Set<string>;
  evaluate(
    result: EvalResult,
    verdicts?: Verdict[],
    context?: Record<string, unknown>,
  ): Suggestion[];
}

export interface FunctionalRuleOptions {
  name?: string;
  appliesTo?: string;
}

class FunctionalRule implements SuggestionRule {
  private readonly fn: (
    result: EvalResult,
    verdicts?: Verdict[],
    context?: Record<string, unknown>,
  ) => Suggestion[];
  private readonly ruleName: string;
  private readonly appliesTo?: string;

  constructor(
    fn: (
      result: EvalResult,
      verdicts?: Verdict[],
      context?: Record<string, unknown>,
    ) => Suggestion[],
    options: FunctionalRuleOptions = {},
  ) {
    this.fn = fn;
    this.ruleName = options.name ?? fn.name;
    this.appliesTo = options.appliesTo;
  }

  evaluate(
    result: EvalResult,
    verdicts?: Verdict[],
    context?: Record<string, unknown>,
  ): Suggestion[] {
    if (this.appliesTo && result.category !== this.appliesTo) {
      return [];
    }
    return this.fn(result, verdicts, context);
  }
}

export function suggestionRule(
  options: FunctionalRuleOptions = {},
): (
  fn: (
    result: EvalResult,
    verdicts?: Verdict[],
    context?: Record<string, unknown>,
  ) => Suggestion[],
) => SuggestionRule {
  return (fn) => new FunctionalRule(fn, options);
}
