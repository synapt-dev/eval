import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  SuggestionEngine,
  LowPrecisionRule,
  LowRecallRule,
  HighNoResultsRule,
  LowSuccessRateRule,
  HallucinationSignalRule,
  VerdictFailureRule,
  RegressionRule,
  CategoryImbalanceRule,
  MonotonicDegradationRule,
  StableLowRule,
  defaultRules,
  suggestionRule,
} from "../src/suggestion_engine/mod.ts";
import {
  SEVERITY_ERROR,
  SEVERITY_INFO,
  SEVERITY_WARNING,
  SEVERITY_CRITICAL,
} from "../src/reviewer/types.ts";
import type { EvalResult, PerFixtureResult } from "../src/types.ts";
import type { Verdict, CheckResult } from "../src/reviewer/types.ts";

function makeResult(opts: {
  category?: string;
  pAt5?: number;
  rAt10?: number;
  n?: number;
  perFixture?: PerFixtureResult[];
}): EvalResult {
  return {
    category: opts.category ?? "test",
    metrics: {
      pAt5: opts.pAt5 ?? 0.8,
      rAt10: opts.rAt10 ?? 0.7,
      n: opts.n ?? 10,
    },
    perFixture: opts.perFixture ?? [],
  };
}

function makeFixture(id: string, score: number): PerFixtureResult {
  return { fixtureId: id, category: "test", passed: score > 0, score };
}

describe("LowPrecisionRule", () => {
  it("flags below threshold", () => {
    const suggestions = new LowPrecisionRule(0.7).evaluate(
      makeResult({ category: "retrieval", pAt5: 0.5 }),
    );
    assert.strictEqual(suggestions.length, 1);
    assert.strictEqual(suggestions[0].ruleName, "low_precision");
  });

  it("passes at threshold", () => {
    const s = new LowPrecisionRule(0.7).evaluate(
      makeResult({ category: "retrieval", pAt5: 0.7 }),
    );
    assert.strictEqual(s.length, 0);
  });
});

describe("LowRecallRule", () => {
  it("flags below threshold", () => {
    const s = new LowRecallRule(0.6).evaluate(
      makeResult({ category: "retrieval", rAt10: 0.4 }),
    );
    assert.strictEqual(s.length, 1);
    assert.strictEqual(s[0].ruleName, "low_recall");
  });

  it("passes at threshold", () => {
    const s = new LowRecallRule(0.6).evaluate(
      makeResult({ category: "retrieval", rAt10: 0.6 }),
    );
    assert.strictEqual(s.length, 0);
  });
});

describe("HighNoResultsRule", () => {
  it("flags high rate", () => {
    const fixtures = [
      ...Array.from({ length: 3 }, (_, i) => makeFixture(`f${i}`, 0)),
      ...Array.from({ length: 7 }, (_, i) => makeFixture(`f${i + 3}`, 0.8)),
    ];
    const s = new HighNoResultsRule(0.1).evaluate(
      makeResult({ category: "retrieval", perFixture: fixtures }),
    );
    assert.strictEqual(s.length, 1);
  });

  it("passes for low rate", () => {
    const fixtures = [
      makeFixture("f0", 0),
      ...Array.from({ length: 19 }, (_, i) => makeFixture(`f${i + 1}`, 0.8)),
    ];
    const s = new HighNoResultsRule(0.1).evaluate(
      makeResult({ category: "retrieval", perFixture: fixtures }),
    );
    assert.strictEqual(s.length, 0);
  });

  it("returns empty for no fixtures", () => {
    const s = new HighNoResultsRule().evaluate(makeResult({ category: "retrieval" }));
    assert.strictEqual(s.length, 0);
  });
});

describe("LowSuccessRateRule", () => {
  it("flags below threshold", () => {
    const s = new LowSuccessRateRule(0.8).evaluate(
      makeResult({ category: "generation", pAt5: 0.5 }),
    );
    assert.strictEqual(s.length, 1);
    assert.strictEqual(s[0].ruleName, "low_success_rate");
  });

  it("passes above threshold", () => {
    const s = new LowSuccessRateRule(0.8).evaluate(
      makeResult({ category: "generation", pAt5: 0.9 }),
    );
    assert.strictEqual(s.length, 0);
  });
});

describe("HallucinationSignalRule", () => {
  it("flags low-score verdicts", () => {
    const verdicts: Verdict[] = [
      {
        passed: false,
        reasoning: "fabricated",
        severity: SEVERITY_ERROR,
        checks: [],
        score: 0.2,
      },
    ];
    const s = new HallucinationSignalRule().evaluate(
      makeResult({ category: "generation" }),
      verdicts,
    );
    assert.strictEqual(s.length, 1);
    assert.strictEqual(s[0].ruleName, "hallucination_signal");
  });

  it("passes for good verdicts", () => {
    const verdicts: Verdict[] = [
      {
        passed: true,
        reasoning: "good",
        severity: SEVERITY_INFO,
        checks: [],
        score: 0.9,
      },
    ];
    const s = new HallucinationSignalRule().evaluate(
      makeResult({ category: "generation" }),
      verdicts,
    );
    assert.strictEqual(s.length, 0);
  });

  it("returns empty with no verdicts", () => {
    const s = new HallucinationSignalRule().evaluate(
      makeResult({ category: "generation" }),
    );
    assert.strictEqual(s.length, 0);
  });
});

describe("VerdictFailureRule", () => {
  it("creates suggestions from failed checks", () => {
    const verdicts: Verdict[] = [
      {
        passed: false,
        reasoning: "issues",
        severity: SEVERITY_ERROR,
        checks: [
          { name: "temporal", passed: false, severity: SEVERITY_WARNING, reasoning: "stale" },
          { name: "relevance", passed: true, severity: SEVERITY_INFO },
        ],
        score: 0.5,
      },
    ];
    const s = new VerdictFailureRule().evaluate(makeResult({}), verdicts);
    assert.strictEqual(s.length, 1);
    assert.ok(s[0].message.includes("temporal"));
  });

  it("returns empty for all passing", () => {
    const verdicts: Verdict[] = [
      {
        passed: true,
        reasoning: "ok",
        severity: SEVERITY_INFO,
        checks: [{ name: "c1", passed: true, severity: SEVERITY_INFO }],
        score: 1.0,
      },
    ];
    const s = new VerdictFailureRule().evaluate(makeResult({}), verdicts);
    assert.strictEqual(s.length, 0);
  });
});

describe("RegressionRule", () => {
  it("detects regression", () => {
    const result = makeResult({ category: "retrieval", pAt5: 0.65, rAt10: 0.45 });
    const baseline = [makeResult({ category: "retrieval", pAt5: 0.80, rAt10: 0.60 })];
    const s = new RegressionRule(0.05).evaluate(result, undefined, {
      baseline,
    });
    assert.strictEqual(s.length, 2);
    assert.ok(s.every((x) => x.ruleName === "regression"));
  });

  it("no regression when improving", () => {
    const result = makeResult({ category: "retrieval", pAt5: 0.85, rAt10: 0.70 });
    const baseline = [makeResult({ category: "retrieval", pAt5: 0.80, rAt10: 0.65 })];
    const s = new RegressionRule().evaluate(result, undefined, { baseline });
    assert.strictEqual(s.length, 0);
  });

  it("returns empty without baseline", () => {
    const s = new RegressionRule().evaluate(makeResult({}));
    assert.strictEqual(s.length, 0);
  });
});

describe("CategoryImbalanceRule", () => {
  it("flags imbalanced categories", () => {
    const allResults = [
      makeResult({ category: "a", n: 100 }),
      makeResult({ category: "b", n: 10 }),
    ];
    const s = new CategoryImbalanceRule(3.0).evaluate(makeResult({}), undefined, {
      all_results: allResults,
    });
    assert.strictEqual(s.length, 1);
    assert.strictEqual(s[0].ruleName, "category_imbalance");
  });

  it("passes for balanced categories", () => {
    const allResults = [
      makeResult({ category: "a", n: 50 }),
      makeResult({ category: "b", n: 40 }),
    ];
    const s = new CategoryImbalanceRule().evaluate(makeResult({}), undefined, {
      all_results: allResults,
    });
    assert.strictEqual(s.length, 0);
  });
});

describe("MonotonicDegradationRule", () => {
  it("detects degrading trend", () => {
    const history = [
      makeResult({ category: "r", pAt5: 0.80 }),
      makeResult({ category: "r", pAt5: 0.75 }),
    ];
    const current = makeResult({ category: "r", pAt5: 0.70 });
    const s = new MonotonicDegradationRule("pAt5", 3).evaluate(current, undefined, {
      history,
    });
    assert.strictEqual(s.length, 1);
    assert.strictEqual(s[0].ruleName, "monotonic_degradation");
  });

  it("passes for improving trend", () => {
    const history = [
      makeResult({ category: "r", pAt5: 0.70 }),
      makeResult({ category: "r", pAt5: 0.75 }),
    ];
    const current = makeResult({ category: "r", pAt5: 0.80 });
    const s = new MonotonicDegradationRule("pAt5", 3).evaluate(current, undefined, {
      history,
    });
    assert.strictEqual(s.length, 0);
  });

  it("returns empty without enough history", () => {
    const s = new MonotonicDegradationRule().evaluate(makeResult({}));
    assert.strictEqual(s.length, 0);
  });
});

describe("StableLowRule", () => {
  it("flags consistently low metric", () => {
    const history = [
      makeResult({ category: "r", pAt5: 0.50 }),
      makeResult({ category: "r", pAt5: 0.55 }),
    ];
    const current = makeResult({ category: "r", pAt5: 0.52 });
    const s = new StableLowRule("pAt5", 0.7, 3).evaluate(current, undefined, {
      history,
    });
    assert.strictEqual(s.length, 1);
    assert.strictEqual(s[0].ruleName, "stable_low");
  });

  it("passes when above threshold", () => {
    const history = [
      makeResult({ category: "r", pAt5: 0.50 }),
      makeResult({ category: "r", pAt5: 0.60 }),
    ];
    const current = makeResult({ category: "r", pAt5: 0.75 });
    const s = new StableLowRule("pAt5", 0.7, 3).evaluate(current, undefined, {
      history,
    });
    assert.strictEqual(s.length, 0);
  });
});

describe("SuggestionEngine", () => {
  it("registers and evaluates rules", () => {
    const engine = new SuggestionEngine();
    engine.register(new LowPrecisionRule(0.7));
    const s = engine.evaluate(makeResult({ category: "retrieval", pAt5: 0.5 }));
    assert.strictEqual(s.length, 1);
  });

  it("category scoping skips wrong category", () => {
    const engine = new SuggestionEngine();
    engine.register(new LowPrecisionRule(0.7));
    const s = engine.evaluate(makeResult({ category: "generation", pAt5: 0.5 }));
    assert.strictEqual(s.length, 0);
  });

  it("orders by severity", () => {
    const engine = new SuggestionEngine();
    engine.register(new LowPrecisionRule(0.9));
    engine.register(new HighNoResultsRule(0.0));
    const result = makeResult({
      category: "retrieval",
      pAt5: 0.5,
      perFixture: [makeFixture("f1", 0), makeFixture("f2", 0.8)],
    });
    const s = engine.evaluate(result);
    assert.strictEqual(s.length, 2);
    assert.ok(s[0].severity.weight >= s[1].severity.weight);
  });

  it("withDefaults has 10 rules", () => {
    const engine = SuggestionEngine.withDefaults();
    assert.strictEqual(engine.rules.length, 10);
  });

  it("evaluateAll aggregates across results", () => {
    const engine = new SuggestionEngine();
    engine.register(new LowPrecisionRule(0.7));
    const results = [
      makeResult({ category: "retrieval", pAt5: 0.5 }),
      makeResult({ category: "retrieval", pAt5: 0.9 }),
    ];
    const s = engine.evaluateAll(results);
    assert.strictEqual(s.length, 1);
  });

  it("empty engine returns empty", () => {
    const engine = new SuggestionEngine();
    const s = engine.evaluate(makeResult({}));
    assert.strictEqual(s.length, 0);
  });
});

describe("defaultRules", () => {
  it("returns 10 rules", () => {
    assert.strictEqual(defaultRules().length, 10);
  });
});

describe("suggestionRule decorator", () => {
  it("creates a functional rule", () => {
    const rule = suggestionRule({ name: "custom" })((result) => {
      if (result.metrics.pAt5 < 0.5) {
        return [
          {
            severity: SEVERITY_CRITICAL,
            message: "Very low precision",
            ruleName: "custom",
          },
        ];
      }
      return [];
    });
    const s = rule.evaluate(makeResult({ pAt5: 0.3 }));
    assert.strictEqual(s.length, 1);
    assert.strictEqual(s[0].ruleName, "custom");
  });

  it("applies category filter", () => {
    const rule = suggestionRule({ appliesTo: "retrieval" })(() => [
      { severity: SEVERITY_INFO, message: "matched", ruleName: "test" },
    ]);
    assert.strictEqual(
      rule.evaluate(makeResult({ category: "retrieval" })).length,
      1,
    );
    assert.strictEqual(
      rule.evaluate(makeResult({ category: "generation" })).length,
      0,
    );
  });
});
