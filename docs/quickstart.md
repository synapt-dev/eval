# Quickstart

This guide walks through a complete retrieval eval in ~60 lines.

## Prerequisites

```bash
pip install synapt-eval
```

## Step 1: Create fixtures

Fixtures define what to query and what results to expect. Create a file `fixtures/retrieval.jsonl`:

```json
{"id": "q1", "query": "python list comprehension", "expected": ["doc_py_lists", "doc_py_comprehension"]}
{"id": "q2", "query": "async await patterns", "expected": ["doc_py_async", "doc_py_concurrency"]}
{"id": "q3", "query": "error handling best practices", "expected": ["doc_py_exceptions", "doc_py_logging"]}
```

## Step 2: Implement your adapter

Connect your retrieval backend to the eval framework:

```python
from synapt_eval.adapters import RetrievalAdapter, RetrievalCandidate


class MyVectorStore(RetrievalAdapter):
    async def retrieve(self, query: str, k: int = 10) -> list[RetrievalCandidate]:
        # Replace with your actual retrieval logic
        results = my_search_api(query, top_k=k)
        return [
            RetrievalCandidate(id=r["id"], score=r["score"])
            for r in results
        ]
```

## Step 3: Run eval and generate report

```python
import asyncio
from synapt_eval import EvalResult, CategoryMetrics
from synapt_eval.scoring import precision_at_k, recall_at_k
from synapt_eval.report_card import compose_report_card, generate_markdown
from synapt_eval.suggestion_engine import SuggestionEngine


async def run_eval():
    adapter = MyVectorStore()

    # Run queries and compute scores
    p5_scores = []
    r10_scores = []
    for fixture in fixtures:
        candidates = await adapter.retrieve(fixture.query, k=10)
        retrieved_ids = [c.id for c in candidates]
        p5_scores.append(precision_at_k(retrieved_ids, fixture.expected, k=5))
        r10_scores.append(recall_at_k(retrieved_ids, fixture.expected, k=10))

    # Aggregate into category metrics
    results = [EvalResult(
        category="retrieval",
        metrics=CategoryMetrics(
            p_at_5=sum(p5_scores) / len(p5_scores),
            r_at_10=sum(r10_scores) / len(r10_scores),
            n=len(p5_scores),
        ),
    )]

    # Generate suggestions
    engine = SuggestionEngine.with_defaults()
    suggestions = engine.evaluate_all(results)

    # Compose and print report card
    card = compose_report_card(results, suggestions=suggestions)
    print(generate_markdown(card))


asyncio.run(run_eval())
```

## Step 4: Add PR gating

Save results as JSON and use the GitHub Action for CI:

```yaml
- name: Run eval
  run: python run_eval.py --output results.json

- uses: synapt-dev/eval@v0.1.0
  with:
    results-path: results.json
    baseline-path: baseline.json
```

See [pr-gate.md](pr-gate.md) for full action configuration.

## Next steps

- [Adapter API](adapter-api.md): write custom adapters for your backend
- [Reviewer Framework](reviewer-framework.md): add policy checks and LLM judges
- [Suggestions](suggestions.md): write custom suggestion rules
- See [examples/retrieval-eval/](../examples/retrieval-eval/) for a runnable version of this guide
