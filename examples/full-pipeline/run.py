"""Full pipeline example: retrieval + generation + reviewer + suggestions + report card.

Run: python examples/full-pipeline/run.py
"""

import asyncio

from synapt_eval import CategoryMetrics, EvalResult
from synapt_eval.adapters import GenerationAdapter, RetrievalAdapter
from synapt_eval.adapters.generation_adapter import GenerationOutput
from synapt_eval.adapters.retrieval_adapter import RetrievalCandidate
from synapt_eval.report_card import compose_report_card, generate_json_string, generate_markdown
from synapt_eval.reviewer import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    CheckResult,
    FrameworkReviewer,
    Predicate,
    ReviewerChain,
)
from synapt_eval.runner.orchestration import pr_gate
from synapt_eval.scoring import precision_at_k, recall_at_k
from synapt_eval.suggestion_engine import SuggestionEngine


class MockRetrieval(RetrievalAdapter):
    async def retrieve(self, query: str, k: int = 10) -> list[RetrievalCandidate]:
        return [RetrievalCandidate(id=f"doc_{i}", score=1.0 - i * 0.1) for i in range(min(k, 3))]


class MockGeneration(GenerationAdapter):
    async def generate(self, query: str, context=None) -> GenerationOutput:
        return GenerationOutput(text=f"Answer to: {query}", latency_ms=45.0)


class ContainsQueryCheck(Predicate):
    """Check that the output references the query topic."""

    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        query_words = query.lower().split()
        found = any(w in output.lower() for w in query_words if len(w) > 3)
        return CheckResult(
            name="contains_query",
            passed=found,
            severity=SEVERITY_ERROR,
            reasoning="Output references query" if found else "Output doesn't reference query",
        )


class MinLengthCheck(Predicate):
    """Check minimum response length."""

    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        ok = len(output) >= 10
        return CheckResult(
            name="min_length",
            passed=ok,
            severity=SEVERITY_WARNING,
            reasoning=f"Length: {len(output)}",
        )


async def main():
    retrieval = MockRetrieval()
    generation = MockGeneration()

    fixtures = [
        {"id": f"q{i}", "query": f"question {i}", "expected": ["doc_0", "doc_1"]} for i in range(10)
    ]

    # -- Retrieval eval --
    p5_scores = []
    r10_scores = []
    for f in fixtures:
        candidates = await retrieval.retrieve(f["query"], k=5)
        retrieved_ids = [c.id for c in candidates]
        p5_scores.append(precision_at_k(retrieved_ids, f["expected"], k=5))
        r10_scores.append(recall_at_k(retrieved_ids, f["expected"], k=10))

    # -- Generation eval with reviewer --
    reviewer = FrameworkReviewer(predicates=[ContainsQueryCheck(), MinLengthCheck()])
    chain = ReviewerChain(reviewers=[reviewer], strategy="strictest")

    gen_successes = 0
    for f in fixtures:
        output = await generation.generate(f["query"])
        verdict = await chain.review(output=output.text, expected=f["expected"], query=f["query"])
        if verdict.passed:
            gen_successes += 1

    results = [
        EvalResult(
            category="retrieval",
            metrics=CategoryMetrics(
                p_at_5=sum(p5_scores) / len(p5_scores),
                r_at_10=sum(r10_scores) / len(r10_scores),
                n=len(fixtures),
            ),
        ),
        EvalResult(
            category="generation",
            metrics=CategoryMetrics(
                p_at_5=gen_successes / len(fixtures),
                r_at_10=gen_successes / len(fixtures),
                n=len(fixtures),
            ),
        ),
    ]

    # -- Suggestion engine --
    engine = SuggestionEngine.with_defaults()
    suggestions = engine.evaluate_all(results)

    # -- PR gate against baseline --
    baseline = [
        EvalResult(
            category="retrieval",
            metrics=CategoryMetrics(p_at_5=0.60, r_at_10=0.55, n=10),
        ),
        EvalResult(
            category="generation",
            metrics=CategoryMetrics(p_at_5=0.90, r_at_10=0.90, n=10),
        ),
    ]

    gate = pr_gate(current=results, baseline=baseline, regression_threshold=0.05)
    print(f"PR Gate: {'PASSED' if gate.passed else 'FAILED'}")
    print(gate.summary)

    # -- Report card --
    card = compose_report_card(
        results,
        suggestions=suggestions,
        baseline=baseline,
        run_id="full-pipeline-example",
        commit="abc123",
    )

    print("\n" + "=" * 60)
    print("MARKDOWN REPORT")
    print("=" * 60)
    print(generate_markdown(card))

    print("\n" + "=" * 60)
    print("JSON REPORT (first 20 lines)")
    print("=" * 60)
    json_str = generate_json_string(card)
    for line in json_str.splitlines()[:20]:
        print(line)
    print("...")


if __name__ == "__main__":
    asyncio.run(main())
