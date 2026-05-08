"""Adapter interfaces for customer integration."""

from synapt_eval.adapters.fixture_loader import FixtureLoader
from synapt_eval.adapters.generation_adapter import GenerationAdapter, GenerationOutput
from synapt_eval.adapters.judge_adapter import JudgeAdapter, JudgeRequest, JudgeResponse
from synapt_eval.adapters.retrieval_adapter import RetrievalAdapter, RetrievalCandidate

__all__ = [
    "FixtureLoader",
    "GenerationAdapter",
    "GenerationOutput",
    "JudgeAdapter",
    "JudgeRequest",
    "JudgeResponse",
    "RetrievalAdapter",
    "RetrievalCandidate",
]
