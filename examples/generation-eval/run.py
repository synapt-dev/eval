"""Generation eval example with mock LLM output and reviewer.

Run: python examples/generation-eval/run.py
"""

import asyncio

from synapt_eval import CategoryMetrics, EvalResult
from synapt_eval.adapters import GenerationAdapter
from synapt_eval.adapters.generation_adapter import GenerationOutput
from synapt_eval.report_card import compose_report_card, generate_markdown
from synapt_eval.reviewer import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    CheckResult,
    FrameworkReviewer,
    Predicate,
)
from synapt_eval.suggestion_engine import SuggestionEngine

FIXTURES = [
    {"id": "g1", "query": "What is Python?", "expected": ["programming", "language"]},
    {"id": "g2", "query": "Explain async/await", "expected": ["coroutine", "event loop"]},
    {"id": "g3", "query": "What is a decorator?", "expected": ["function", "wraps"]},
]


class MockLLM(GenerationAdapter):
    async def generate(self, query: str, context=None) -> GenerationOutput:
        responses = {
            "What is Python?": (
                "Python is a high-level programming language known for readability."
            ),
            "Explain async/await": (
                "Async/await enables coroutine-based concurrency with an event loop."
            ),
            "What is a decorator?": (
                "A decorator is a function that wraps another function to extend behavior."
            ),
        }
        return GenerationOutput(
            text=responses.get(query, "I don't know."),
            latency_ms=50.0,
        )


class KeywordPresenceCheck(Predicate):
    """Check that expected keywords appear in the output."""

    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        missing = [kw for kw in expected if kw.lower() not in output.lower()]
        if missing:
            return CheckResult(
                name="keyword_presence",
                passed=False,
                severity=SEVERITY_ERROR,
                reasoning=f"Missing keywords: {', '.join(missing)}",
            )
        return CheckResult(
            name="keyword_presence",
            passed=True,
            severity=SEVERITY_ERROR,
            reasoning="All expected keywords found",
        )


class MinLengthCheck(Predicate):
    """Check that output meets a minimum length."""

    def __init__(self, min_length: int = 20):
        self.min_length = min_length

    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        if len(output) < self.min_length:
            return CheckResult(
                name="min_length",
                passed=False,
                severity=SEVERITY_WARNING,
                reasoning=f"Output length {len(output)} below minimum {self.min_length}",
            )
        return CheckResult(
            name="min_length",
            passed=True,
            severity=SEVERITY_WARNING,
            reasoning=f"Output length {len(output)} meets minimum",
        )


async def main():
    adapter = MockLLM()
    reviewer = FrameworkReviewer(predicates=[KeywordPresenceCheck(), MinLengthCheck(min_length=20)])

    successes = 0
    for fixture in FIXTURES:
        output = await adapter.generate(fixture["query"])
        verdict = await reviewer.review(
            output=output.text,
            expected=fixture["expected"],
            query=fixture["query"],
        )
        status = "PASS" if verdict.passed else "FAIL"
        print(f"  {fixture['id']}: {status} (score: {verdict.score:.2f}) - {verdict.reasoning}")
        if verdict.passed:
            successes += 1

    print()

    results = [
        EvalResult(
            category="generation",
            metrics=CategoryMetrics(
                p_at_5=successes / len(FIXTURES),
                r_at_10=successes / len(FIXTURES),
                n=len(FIXTURES),
            ),
        )
    ]

    engine = SuggestionEngine.with_defaults()
    suggestions = engine.evaluate_all(results)

    card = compose_report_card(results, suggestions=suggestions, run_id="generation-example")
    print(generate_markdown(card))


if __name__ == "__main__":
    asyncio.run(main())
