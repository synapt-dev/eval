import type { Reviewer } from "./protocol.ts";
import { SEVERITY_INFO, type CheckResult, type Verdict } from "./types.ts";

export type ChainStrategy = "strictest" | "majority" | "weighted";

export class ReviewerChain implements Reviewer {
  private readonly reviewers: Reviewer[];
  private readonly strategy: ChainStrategy;

  constructor(reviewers: Reviewer[], strategy: ChainStrategy = "strictest") {
    this.reviewers = reviewers;
    this.strategy = strategy;
  }

  async review(
    output: string,
    expected: string[],
    query: string,
  ): Promise<Verdict> {
    const verdicts: Verdict[] = [];
    for (const reviewer of this.reviewers) {
      verdicts.push(await reviewer.review(output, expected, query));
    }
    return this.resolve(verdicts);
  }

  private resolve(verdicts: Verdict[]): Verdict {
    if (verdicts.length === 0) {
      return {
        passed: true,
        reasoning: "No reviewers in chain",
        severity: SEVERITY_INFO,
        checks: [],
        score: 1.0,
      };
    }

    const allChecks: CheckResult[] = verdicts.flatMap((v) => v.checks);
    const avgScore =
      verdicts.reduce((sum, v) => sum + v.score, 0) / verdicts.length;

    switch (this.strategy) {
      case "strictest":
        return this.resolveStrictest(verdicts, allChecks, avgScore);
      case "majority":
        return this.resolveMajority(verdicts, allChecks, avgScore);
      case "weighted":
        return this.resolveWeighted(verdicts, allChecks);
      default:
        throw new Error(`Unknown strategy: ${this.strategy}`);
    }
  }

  private resolveStrictest(
    verdicts: Verdict[],
    allChecks: CheckResult[],
    avgScore: number,
  ): Verdict {
    const failed = verdicts.filter((v) => !v.passed);
    if (failed.length === 0) {
      return {
        passed: true,
        reasoning: "All reviewers passed",
        severity: SEVERITY_INFO,
        checks: allChecks,
        score: avgScore,
      };
    }
    const worst = failed.reduce((a, b) =>
      a.severity.weight >= b.severity.weight ? a : b,
    );
    const reasons = failed.map((v) => v.reasoning);
    return {
      passed: false,
      reasoning: `${failed.length} reviewer(s) failed: ${reasons.join("; ")}`,
      severity: worst.severity,
      checks: allChecks,
      score: avgScore,
    };
  }

  private resolveMajority(
    verdicts: Verdict[],
    allChecks: CheckResult[],
    avgScore: number,
  ): Verdict {
    const passCount = verdicts.filter((v) => v.passed).length;
    const passed = passCount > verdicts.length / 2;
    if (passed) {
      return {
        passed: true,
        reasoning: `Majority passed (${passCount}/${verdicts.length})`,
        severity: SEVERITY_INFO,
        checks: allChecks,
        score: avgScore,
      };
    }
    const failed = verdicts.filter((v) => !v.passed);
    const worst = failed.reduce((a, b) =>
      a.severity.weight >= b.severity.weight ? a : b,
    );
    return {
      passed: false,
      reasoning: `Majority failed (${failed.length}/${verdicts.length})`,
      severity: worst.severity,
      checks: allChecks,
      score: avgScore,
    };
  }

  private resolveWeighted(
    verdicts: Verdict[],
    allChecks: CheckResult[],
  ): Verdict {
    const totalWeight = verdicts.reduce(
      (sum, v) => sum + v.severity.weight,
      0,
    );
    if (totalWeight === 0) {
      return {
        passed: true,
        reasoning: "No weighted signal",
        severity: SEVERITY_INFO,
        checks: allChecks,
        score: 1.0,
      };
    }
    const weightedScore =
      verdicts.reduce((sum, v) => sum + v.score * v.severity.weight, 0) /
      totalWeight;
    const passed = weightedScore >= 0.5;
    const worstFailing = verdicts.filter((v) => !v.passed);
    const severity =
      worstFailing.length > 0
        ? worstFailing.reduce((a, b) =>
            a.severity.weight >= b.severity.weight ? a : b,
          ).severity
        : SEVERITY_INFO;
    return {
      passed,
      reasoning: `Weighted score: ${weightedScore.toFixed(2)}`,
      severity,
      checks: allChecks,
      score: weightedScore,
    };
  }
}
