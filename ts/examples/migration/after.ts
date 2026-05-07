/**
 * AFTER: Composable eval with @synapt/eval.
 *
 * Benefits:
 * - Adapter pattern decouples eval from backend implementation
 * - Structured scoring with standard metrics
 * - Suggestion engine flags issues with actionable fix hints
 * - Report card output is CI/CD-ready (markdown + JSON)
 * - Adding generation eval is one new adapter, not a rewrite
 * - Regression detection via baseline comparison
 */

import {
  type EvalResult,
  type RetrievalAdapter,
  type RetrievalCandidate,
  precisionAtK,
  recallAtK,
  SuggestionEngine,
  composeReportCard,
  generateMarkdown,
} from "../../src/mod.ts";

// Step 1: Implement the adapter for your retrieval backend.
// This is the ONLY code that knows about your infrastructure.
class ConversaRetrievalAdapter implements RetrievalAdapter {
  async retrieve(query: string, k = 10): Promise<RetrievalCandidate[]> {
    // Replace with your actual retrieval call
    const mockResults: Record<string, string[]> = {
      "billing history": ["doc_billing", "doc_invoices", "doc_payments"],
      "password reset": ["doc_auth", "doc_security", "doc_settings"],
      "shipping status": ["doc_orders", "doc_tracking", "doc_returns"],
    };
    const docs = (mockResults[query] ?? []).slice(0, k);
    return docs.map((id, i) => ({ id, score: 1.0 - i * 0.1 }));
  }
}

// Step 2: Define fixtures (same shape, now typed).
const fixtures = [
  { id: "q1", query: "billing history", expected: ["doc_billing", "doc_invoices"] },
  { id: "q2", query: "password reset", expected: ["doc_auth", "doc_security"] },
  { id: "q3", query: "shipping status", expected: ["doc_orders", "doc_tracking"] },
];

async function main() {
  const adapter = new ConversaRetrievalAdapter();

  // Step 3: Run eval using standard scoring primitives.
  const p5Scores: number[] = [];
  const r10Scores: number[] = [];

  for (const fixture of fixtures) {
    const candidates = await adapter.retrieve(fixture.query, 5);
    const retrievedIds = candidates.map((c) => c.id);
    p5Scores.push(precisionAtK(retrievedIds, fixture.expected, 5));
    r10Scores.push(recallAtK(retrievedIds, fixture.expected, 10));
  }

  const results: EvalResult[] = [
    {
      category: "retrieval",
      metrics: {
        pAt5: p5Scores.reduce((a, b) => a + b, 0) / p5Scores.length,
        rAt10: r10Scores.reduce((a, b) => a + b, 0) / r10Scores.length,
        n: fixtures.length,
      },
    },
  ];

  // Step 4: Run suggestion engine (replaces ad-hoc threshold checks).
  const engine = SuggestionEngine.withDefaults();
  const suggestions = engine.evaluateAll(results);

  // Step 5: Compose and render the report card.
  const card = composeReportCard({
    results,
    suggestions,
    runId: "conversa-migration-demo",
  });
  console.log(generateMarkdown(card));

  // The same results JSON feeds the GitHub Action for PR gating:
  // - Write results to a JSON file
  // - uses: synapt-dev/eval@v0.1.0 with results-path: ./eval-results.json
}

main();
