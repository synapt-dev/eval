import type { Predicate, Reviewer } from "./protocol.ts";
import { SEVERITY_INFO, type CheckResult, type Verdict } from "./types.ts";

export class FrameworkReviewer implements Reviewer {
  private readonly predicates: Predicate[];

  constructor(predicates: Predicate[]) {
    this.predicates = predicates;
  }

  async review(
    output: string,
    expected: string[],
    query: string,
  ): Promise<Verdict> {
    const checks: CheckResult[] = this.predicates.map((p) =>
      p.check(output, expected, query),
    );
    const failed = checks.filter((c) => !c.passed);

    if (failed.length === 0) {
      return {
        passed: true,
        reasoning: "All checks passed",
        severity: SEVERITY_INFO,
        checks,
        score: 1.0,
      };
    }

    const worst = failed.reduce((a, b) =>
      a.severity.weight >= b.severity.weight ? a : b,
    );
    const score = checks.length > 0
      ? checks.filter((c) => c.passed).length / checks.length
      : 0;

    return {
      passed: false,
      reasoning: `${failed.length} check(s) failed: ${failed.map((c) => c.name).join(", ")}`,
      severity: worst.severity,
      checks,
      score,
    };
  }
}
