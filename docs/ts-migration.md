# TypeScript Migration Guide

Migrate from a monolithic eval script to composable `@synapt/eval` adapters.

## Before vs After

See the working examples in `ts/examples/migration/`:
- `before.ts` - Monolithic pattern with inline scoring and ad-hoc reporting
- `after.ts` - Composable pattern with adapters, suggestion engine, and report cards

## Migration Steps

### 1. Define Your Adapter

Extract your retrieval/generation call into an adapter class:

```typescript
import type { RetrievalAdapter, RetrievalCandidate } from "@synapt/eval";

class MyRetrievalAdapter implements RetrievalAdapter {
  async retrieve(query: string, k = 10): Promise<RetrievalCandidate[]> {
    const results = await myBackend.search(query, k);
    return results.map((r) => ({ id: r.id, score: r.score }));
  }
}
```

### 2. Replace Inline Scoring

Replace hand-rolled precision/recall with standard primitives:

```typescript
import { precisionAtK, recallAtK } from "@synapt/eval";

const p5 = precisionAtK(retrievedIds, expectedIds, 5);
const r10 = recallAtK(retrievedIds, expectedIds, 10);
```

### 3. Replace Threshold Checks with Suggestion Engine

Replace `if (p5 < 0.5) failures.push(...)` with:

```typescript
import { SuggestionEngine } from "@synapt/eval";

const engine = SuggestionEngine.withDefaults();
const suggestions = engine.evaluateAll(results);
// Each suggestion has severity, fix hint, and rule name
```

### 4. Generate Report Cards

Replace `console.log` with structured output:

```typescript
import { composeReportCard, generateMarkdown } from "@synapt/eval";

const card = composeReportCard({ results, suggestions });
console.log(generateMarkdown(card));
```

### 5. Add CI/CD Integration

Write results to JSON and use the GitHub Action:

```yaml
- uses: synapt-dev/eval@v0.1.0
  with:
    results-path: ./eval-results.json
    fail-on: error
```

## Adding Generation Eval

With adapters, adding generation eval is one new class:

```typescript
import type { GenerationAdapter, GenerationOutput } from "@synapt/eval";

class MyGenerationAdapter implements GenerationAdapter {
  async generate(query: string, context?: unknown[]): Promise<GenerationOutput> {
    const response = await myLLM.complete(query);
    return { text: response.text, latencyMs: response.elapsed };
  }
}
```

## Adding Custom Rules

Extend the suggestion engine with domain-specific rules:

```typescript
import { SuggestionEngine, suggestionRule, SEVERITY_WARNING } from "@synapt/eval";

const latencyRule = suggestionRule({ name: "high_latency" })((result) => {
  // Custom rule for your domain
  return [];
});

const engine = SuggestionEngine.withDefaults();
engine.register(latencyRule);
```
