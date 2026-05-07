"""Retrieval eval example with mock fixtures and adapter.

Run: python examples/retrieval-eval/run.py
"""

import asyncio

from synapt_eval import CategoryMetrics, EvalResult
from synapt_eval.adapters import RetrievalAdapter
from synapt_eval.adapters.retrieval_adapter import RetrievalCandidate
from synapt_eval.report_card import compose_report_card, generate_markdown
from synapt_eval.scoring import precision_at_k, recall_at_k
from synapt_eval.suggestion_engine import SuggestionEngine

FIXTURES = [
    {
        "id": "q1",
        "query": "python list comprehension",
        "expected": ["doc_py_lists", "doc_py_comprehension"],
    },
    {
        "id": "q2",
        "query": "async await patterns",
        "expected": ["doc_py_async", "doc_py_concurrency"],
    },
    {"id": "q3", "query": "error handling", "expected": ["doc_py_exceptions", "doc_py_logging"]},
    {"id": "q4", "query": "data classes", "expected": ["doc_py_dataclass", "doc_py_attrs"]},
    {"id": "q5", "query": "type hints", "expected": ["doc_py_typing", "doc_py_mypy"]},
]

MOCK_INDEX = {
    "python list comprehension": ["doc_py_lists", "doc_py_comprehension", "doc_py_loops"],
    "async await patterns": ["doc_py_async", "doc_unrelated", "doc_py_concurrency"],
    "error handling": ["doc_py_exceptions", "doc_py_logging", "doc_py_testing"],
    "data classes": ["doc_py_dataclass", "doc_py_namedtuple", "doc_py_attrs"],
    "type hints": ["doc_py_typing", "doc_py_generics", "doc_py_mypy"],
}


class MockRetrievalAdapter(RetrievalAdapter):
    async def retrieve(self, query: str, k: int = 10) -> list[RetrievalCandidate]:
        docs = MOCK_INDEX.get(query, [])[:k]
        return [RetrievalCandidate(id=doc_id, score=1.0 - i * 0.1) for i, doc_id in enumerate(docs)]


async def main():
    adapter = MockRetrievalAdapter()

    p5_scores = []
    r10_scores = []

    for fixture in FIXTURES:
        candidates = await adapter.retrieve(fixture["query"], k=5)
        retrieved_ids = [c.id for c in candidates]
        p5_scores.append(precision_at_k(retrieved_ids, fixture["expected"], k=5))
        r10_scores.append(recall_at_k(retrieved_ids, fixture["expected"], k=10))

    results = [
        EvalResult(
            category="retrieval",
            metrics=CategoryMetrics(
                p_at_5=sum(p5_scores) / len(p5_scores),
                r_at_10=sum(r10_scores) / len(r10_scores),
                n=len(FIXTURES),
            ),
        )
    ]

    engine = SuggestionEngine.with_defaults()
    suggestions = engine.evaluate_all(results)

    card = compose_report_card(results, suggestions=suggestions, run_id="retrieval-example")
    print(generate_markdown(card))


if __name__ == "__main__":
    asyncio.run(main())
