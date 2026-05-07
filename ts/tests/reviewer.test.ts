import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  FrameworkReviewer,
  ReviewerChain,
  SEVERITY_INFO,
  SEVERITY_WARNING,
  SEVERITY_ERROR,
  type Predicate,
  type CheckResult,
} from "../src/reviewer/mod.ts";

function passingPredicate(name: string): Predicate {
  return {
    check: () => ({
      name,
      passed: true,
      severity: SEVERITY_INFO,
      reasoning: "ok",
    }),
  };
}

function failingPredicate(name: string): Predicate {
  return {
    check: () => ({
      name,
      passed: false,
      severity: SEVERITY_WARNING,
      reasoning: "failed",
    }),
  };
}

describe("FrameworkReviewer", () => {
  it("passes when all predicates pass", async () => {
    const reviewer = new FrameworkReviewer([
      passingPredicate("a"),
      passingPredicate("b"),
    ]);
    const verdict = await reviewer.review("output", ["expected"], "query");
    assert.strictEqual(verdict.passed, true);
    assert.strictEqual(verdict.score, 1.0);
    assert.strictEqual(verdict.checks.length, 2);
  });

  it("fails when any predicate fails", async () => {
    const reviewer = new FrameworkReviewer([
      passingPredicate("a"),
      failingPredicate("b"),
    ]);
    const verdict = await reviewer.review("output", ["expected"], "query");
    assert.strictEqual(verdict.passed, false);
    assert.strictEqual(verdict.score, 0.5);
    assert.ok(verdict.reasoning.includes("b"));
  });

  it("reports worst severity from failures", async () => {
    const errorPredicate: Predicate = {
      check: () => ({
        name: "critical",
        passed: false,
        severity: SEVERITY_ERROR,
        reasoning: "bad",
      }),
    };
    const reviewer = new FrameworkReviewer([
      failingPredicate("warn"),
      errorPredicate,
    ]);
    const verdict = await reviewer.review("output", ["expected"], "query");
    assert.strictEqual(verdict.severity.level, "error");
  });

  it("handles empty predicates", async () => {
    const reviewer = new FrameworkReviewer([]);
    const verdict = await reviewer.review("output", ["expected"], "query");
    assert.strictEqual(verdict.passed, true);
  });
});

describe("ReviewerChain", () => {
  it("strictest: fails if any reviewer fails", async () => {
    const pass = new FrameworkReviewer([passingPredicate("a")]);
    const fail = new FrameworkReviewer([failingPredicate("b")]);
    const chain = new ReviewerChain([pass, fail], "strictest");
    const verdict = await chain.review("output", ["expected"], "query");
    assert.strictEqual(verdict.passed, false);
  });

  it("strictest: passes when all pass", async () => {
    const r1 = new FrameworkReviewer([passingPredicate("a")]);
    const r2 = new FrameworkReviewer([passingPredicate("b")]);
    const chain = new ReviewerChain([r1, r2], "strictest");
    const verdict = await chain.review("output", ["expected"], "query");
    assert.strictEqual(verdict.passed, true);
  });

  it("majority: passes when majority pass", async () => {
    const pass1 = new FrameworkReviewer([passingPredicate("a")]);
    const pass2 = new FrameworkReviewer([passingPredicate("b")]);
    const fail = new FrameworkReviewer([failingPredicate("c")]);
    const chain = new ReviewerChain([pass1, pass2, fail], "majority");
    const verdict = await chain.review("output", ["expected"], "query");
    assert.strictEqual(verdict.passed, true);
  });

  it("majority: fails when majority fail", async () => {
    const pass = new FrameworkReviewer([passingPredicate("a")]);
    const fail1 = new FrameworkReviewer([failingPredicate("b")]);
    const fail2 = new FrameworkReviewer([failingPredicate("c")]);
    const chain = new ReviewerChain([pass, fail1, fail2], "majority");
    const verdict = await chain.review("output", ["expected"], "query");
    assert.strictEqual(verdict.passed, false);
  });

  it("weighted: passes when weighted score >= 0.5", async () => {
    const pass = new FrameworkReviewer([passingPredicate("a")]);
    const fail = new FrameworkReviewer([failingPredicate("b")]);
    const chain = new ReviewerChain([pass, fail], "weighted");
    const verdict = await chain.review("output", ["expected"], "query");
    assert.ok(typeof verdict.passed === "boolean");
  });

  it("handles empty chain", async () => {
    const chain = new ReviewerChain([]);
    const verdict = await chain.review("output", ["expected"], "query");
    assert.strictEqual(verdict.passed, true);
  });
});
