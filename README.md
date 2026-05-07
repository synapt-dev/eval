# @synapt/eval

Domain-agnostic eval framework for AI applications. Measure retrieval quality, generation accuracy, and policy compliance across any vertical.

## Install

```bash
pip install synapt-eval
```

## Quick Start

```python
from synapt_eval import Fixture, CategoryMetrics
from synapt_eval.scoring import precision_at_k, recall_at_k, kendall_tau
from synapt_eval.adapters import RetrievalAdapter, GenerationAdapter, FixtureLoader

# 1. Define your fixtures (JSONL files or custom loader)
# 2. Implement adapters for your retrieval/generation backend
# 3. Run eval and get a report card
```

## Architecture

synapt-eval separates the **eval framework** (scoring, aggregation, reporting) from **domain-specific adapters** (your retrieval backend, your generation pipeline, your fixtures).

```
synapt-eval (framework)          Your code (adapters)
---------------------          --------------------
Scoring math                   RetrievalAdapter
Fixture loading                GenerationAdapter
Aggregation                    FixtureLoader
Report card                    Policy checks
Suggestion engine              Domain fixtures
```

## Scoring Primitives

- **Precision@K**: fraction of top-K retrieved items that are relevant
- **Recall@K**: fraction of relevant items found in top-K
- **Kendall's Tau**: rank correlation between expected and actual orderings

## Adapter Pattern

Customers implement three interfaces to connect their system:

- `RetrievalAdapter`: connect your vector store / search backend
- `GenerationAdapter`: connect your LLM pipeline
- `FixtureLoader`: load fixtures from your data source

## License

MIT
