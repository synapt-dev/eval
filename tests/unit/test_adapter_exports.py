"""Public adapter export contract used by README and docs."""

from synapt_eval.adapters import (
    GenerationAdapter,
    GenerationOutput,
    RetrievalAdapter,
    RetrievalCandidate,
)


def test_documented_adapter_imports_are_exported() -> None:
    assert RetrievalAdapter.__name__ == "RetrievalAdapter"
    assert RetrievalCandidate(id="doc1", score=0.9).id == "doc1"
    assert GenerationAdapter.__name__ == "GenerationAdapter"
    assert GenerationOutput(text="ok", latency_ms=1.0).text == "ok"
