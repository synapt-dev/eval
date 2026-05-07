"""Main eval runner: wires fixtures + adapters + scoring into a complete run."""

from __future__ import annotations

import asyncio
from pathlib import Path

from synapt_eval.adapters.fixture_loader import FixtureLoader, JsonFixtureLoader
from synapt_eval.adapters.generation_adapter import GenerationAdapter
from synapt_eval.adapters.retrieval_adapter import RetrievalAdapter
from synapt_eval.runner.generation import run_generation_category
from synapt_eval.runner.orchestration import GateResult, RunEnvelope, load_baseline, pr_gate
from synapt_eval.runner.retrieval import run_retrieval_category
from synapt_eval.types import EvalConfig, EvalResult


class EvalRunner:
    """Orchestrates a complete eval run across categories.

    Wires together fixtures, adapters, and scoring into a single
    async run() call that returns a RunEnvelope.
    """

    def __init__(
        self,
        config: EvalConfig,
        retrieval_adapter: RetrievalAdapter | None = None,
        generation_adapter: GenerationAdapter | None = None,
        fixture_loader: FixtureLoader | None = None,
    ) -> None:
        self.config = config
        self.retrieval = retrieval_adapter
        self.generation = generation_adapter
        self.loader = fixture_loader or JsonFixtureLoader(config.fixtures_path)

    async def run(self) -> RunEnvelope:
        """Run eval across all configured categories."""
        await self.loader.setup()

        results: list[EvalResult] = []

        for category in self.config.categories:
            fixtures = await self.loader.load(category)
            if not fixtures:
                continue

            if self.retrieval is not None:
                result = await run_retrieval_category(fixtures, self.retrieval, category)
                results.append(result)

            if self.generation is not None:
                result = await run_generation_category(fixtures, self.generation, category)
                results.append(result)

        await self.loader.cleanup()

        envelope = RunEnvelope.create(
            results=results,
            config={
                "fixtures_path": self.config.fixtures_path,
                "categories": self.config.categories,
            },
        )

        if self.config.output_path:
            envelope.save(self.config.output_path)

        return envelope

    async def run_with_gate(
        self,
        baseline_path: str | Path | None = None,
        regression_threshold: float = 0.05,
    ) -> tuple[RunEnvelope, GateResult | None]:
        """Run eval and compare against baseline for PR gating."""
        envelope = await self.run()

        gate_result: GateResult | None = None
        if baseline_path is not None:
            baseline = load_baseline(baseline_path)
            if baseline is not None:
                gate_result = pr_gate(envelope.results, baseline, regression_threshold)
                envelope.baseline_id = str(baseline_path)

        return envelope, gate_result


def run_eval_sync(
    config: EvalConfig,
    retrieval_adapter: RetrievalAdapter | None = None,
    generation_adapter: GenerationAdapter | None = None,
    fixture_loader: FixtureLoader | None = None,
) -> RunEnvelope:
    """Sync convenience wrapper for one-shot eval runs."""
    runner = EvalRunner(
        config=config,
        retrieval_adapter=retrieval_adapter,
        generation_adapter=generation_adapter,
        fixture_loader=fixture_loader,
    )
    return asyncio.run(runner.run())
