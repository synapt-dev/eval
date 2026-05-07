import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { composeReportCard, generateMarkdown } from "../src/report_card/mod.ts";
import { SEVERITY_WARNING, SEVERITY_ERROR } from "../src/reviewer/types.ts";
import type { EvalResult } from "../src/types.ts";
import type { Suggestion } from "../src/suggestion_engine/types.ts";

function makeResult(
  category: string,
  pAt5: number,
  rAt10: number,
  n: number,
): EvalResult {
  return { category, metrics: { pAt5, rAt10, n } };
}

function makeSuggestion(
  rule: string,
  category: string,
  level: "warning" | "error",
): Suggestion {
  return {
    severity: level === "error" ? SEVERITY_ERROR : SEVERITY_WARNING,
    message: `${rule} issue`,
    ruleName: rule,
    category,
  };
}

describe("composeReportCard", () => {
  it("builds card from results", () => {
    const results = [makeResult("retrieval", 0.8, 0.7, 10)];
    const card = composeReportCard({ results, runId: "test-run" });
    assert.strictEqual(card.header.runId, "test-run");
    assert.strictEqual(card.header.fixtureCount, 10);
    assert.strictEqual(card.header.categoryCount, 1);
    assert.strictEqual(card.sections.length, 1);
    assert.strictEqual(card.footer.passed, true);
  });

  it("includes suggestions in sections", () => {
    const results = [makeResult("retrieval", 0.5, 0.4, 10)];
    const suggestions = [makeSuggestion("low_precision", "retrieval", "warning")];
    const card = composeReportCard({ results, suggestions });
    assert.strictEqual(card.sections[0].suggestions.length, 1);
  });

  it("detects regressions from baseline", () => {
    const results = [makeResult("retrieval", 0.5, 0.4, 10)];
    const baseline = [makeResult("retrieval", 0.8, 0.7, 10)];
    const card = composeReportCard({ results, baseline });
    assert.strictEqual(card.footer.passed, false);
    assert.ok(card.footer.regressionSummary);
    assert.ok(card.footer.deltas.length > 0);
  });

  it("passes with no issues", () => {
    const results = [makeResult("retrieval", 0.9, 0.85, 10)];
    const card = composeReportCard({ results });
    assert.strictEqual(card.footer.passed, true);
    assert.strictEqual(card.footer.totalSuggestions, 0);
  });

  it("fails with errors", () => {
    const results = [makeResult("retrieval", 0.5, 0.4, 10)];
    const suggestions = [makeSuggestion("critical", "retrieval", "error")];
    const card = composeReportCard({ results, suggestions });
    assert.strictEqual(card.footer.passed, false);
    assert.strictEqual(card.footer.errorCount, 1);
  });

  it("includes commit in header", () => {
    const results = [makeResult("retrieval", 0.8, 0.7, 10)];
    const card = composeReportCard({
      results,
      commit: "abc123",
    });
    assert.strictEqual(card.header.commit, "abc123");
  });

  it("builds trending from history", () => {
    const results = [makeResult("retrieval", 0.8, 0.7, 10)];
    const history = [
      makeResult("retrieval", 0.75, 0.65, 10),
      makeResult("retrieval", 0.78, 0.68, 10),
    ];
    const card = composeReportCard({ results, history });
    assert.strictEqual(card.trending.length, 2);
  });
});

describe("generateMarkdown", () => {
  it("produces valid markdown", () => {
    const results = [makeResult("retrieval", 0.8, 0.7, 10)];
    const suggestions = [makeSuggestion("low_precision", "retrieval", "warning")];
    const card = composeReportCard({
      results,
      suggestions,
      runId: "md-test",
    });
    const md = generateMarkdown(card);
    assert.ok(md.includes("# Eval Report Card"));
    assert.ok(md.includes("md-test"));
    assert.ok(md.includes("## retrieval"));
    assert.ok(md.includes("0.800"));
    assert.ok(md.includes("PASSED"));
  });

  it("shows FAILED for regression", () => {
    const results = [makeResult("retrieval", 0.5, 0.4, 10)];
    const baseline = [makeResult("retrieval", 0.8, 0.7, 10)];
    const card = composeReportCard({ results, baseline });
    const md = generateMarkdown(card);
    assert.ok(md.includes("FAILED"));
    assert.ok(md.includes("REGRESSION"));
  });

  it("includes suggestion table", () => {
    const results = [makeResult("retrieval", 0.5, 0.4, 10)];
    const suggestions = [
      makeSuggestion("low_precision", "retrieval", "warning"),
      makeSuggestion("regression", "retrieval", "error"),
    ];
    const card = composeReportCard({ results, suggestions });
    const md = generateMarkdown(card);
    assert.ok(md.includes("Suggestions Summary"));
    assert.ok(md.includes("low_precision"));
    assert.ok(md.includes("regression"));
  });

  it("includes trending table when present", () => {
    const results = [makeResult("retrieval", 0.8, 0.7, 10)];
    const history = [makeResult("retrieval", 0.75, 0.65, 10)];
    const card = composeReportCard({ results, history });
    const md = generateMarkdown(card);
    assert.ok(md.includes("## Trending"));
  });
});
