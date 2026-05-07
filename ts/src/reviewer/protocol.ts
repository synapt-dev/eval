import type { CheckResult, Verdict } from "./types.ts";

export interface Reviewer {
  review(
    output: string,
    expected: string[],
    query: string,
  ): Promise<Verdict>;
}

export interface Predicate {
  check(output: string, expected: string[], query: string): CheckResult;
}
