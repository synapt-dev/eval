"""Adapter interfaces for customer integration."""

from synapt_eval.adapters.fixture_loader import FixtureLoader
from synapt_eval.adapters.generation_adapter import GenerationAdapter
from synapt_eval.adapters.retrieval_adapter import RetrievalAdapter

__all__ = ["FixtureLoader", "GenerationAdapter", "RetrievalAdapter"]
