/**
 * BEFORE: Monolithic eval pattern (typical pre-@synapt/eval approach).
 *
 * Problems with this pattern:
 * - Scoring, assertion, and reporting are interleaved
 * - No adapter abstraction; retrieval logic is inline
 * - No structured suggestions or regression detection
 * - Results format is ad-hoc (not composable with CI/CD)
 * - Adding generation eval requires duplicating the loop structure
 */

interface Fixture {
  id: string;
  query: string;
  expected: string[];
}

async function retrieveFromBackend(
  query: string,
  k: number,
): Promise<string[]> {
  // Inline retrieval call; tightly coupled to one backend
  return ["doc_1", "doc_2", "doc_3"].slice(0, k);
}

async function runEval(fixtures: Fixture[]) {
  let totalP5 = 0;
  let totalR10 = 0;
  const failures: string[] = [];

  for (const fixture of fixtures) {
    const retrieved = await retrieveFromBackend(fixture.query, 5);
    const relevantSet = new Set(fixture.expected);
    const hits = retrieved.filter((id) => relevantSet.has(id)).length;
    const p5 = hits / retrieved.length;
    const r10 = hits / relevantSet.size;

    totalP5 += p5;
    totalR10 += r10;

    // Inline threshold check; no structured rule system
    if (p5 < 0.5) {
      failures.push(`${fixture.id}: precision too low (${p5})`);
    }
  }

  const avgP5 = totalP5 / fixtures.length;
  const avgR10 = totalR10 / fixtures.length;

  // Ad-hoc console output; not machine-parseable
  console.log(`P@5: ${avgP5.toFixed(3)}`);
  console.log(`R@10: ${avgR10.toFixed(3)}`);
  if (failures.length > 0) {
    console.log(`FAILURES:\n${failures.join("\n")}`);
    process.exit(1);
  }
}

const fixtures: Fixture[] = [
  { id: "q1", query: "billing history", expected: ["doc_billing", "doc_invoices"] },
  { id: "q2", query: "password reset", expected: ["doc_auth", "doc_security"] },
  { id: "q3", query: "shipping status", expected: ["doc_orders", "doc_tracking"] },
];

runEval(fixtures);
