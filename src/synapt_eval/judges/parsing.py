"""Shared JSON parsing for LLM judge responses."""

from __future__ import annotations

import json
import re

from synapt_eval.adapters.judge_adapter import JudgeResponse


def parse_judge_json(content: str) -> JudgeResponse:
    """Parse a structured judge response from raw LLM output.

    Handles common failure modes: markdown fences, missing fields,
    malformed JSON, refusal patterns.
    """
    cleaned = _strip_markdown_fences(content)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return JudgeResponse(
            passed=False,
            score=0.0,
            reasoning=f"Failed to parse judge response as JSON: {content[:200]}",
            raw={"raw_content": content},
        )

    if not isinstance(data, dict):
        return JudgeResponse(
            passed=False,
            score=0.0,
            reasoning=f"Judge response is not a JSON object: {type(data).__name__}",
            raw={"raw_content": content},
        )

    passed = _extract_bool(data, "passed")
    score = _extract_float(data, "score", default=1.0 if passed else 0.0)
    reasoning = str(data.get("reasoning", data.get("explanation", "")))

    return JudgeResponse(
        passed=passed,
        score=max(0.0, min(1.0, score)),
        reasoning=reasoning,
        raw=data,
    )


def _strip_markdown_fences(content: str) -> str:
    """Remove ```json ... ``` wrappers that LLMs commonly add."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()


def _extract_bool(data: dict, key: str) -> bool:
    value = data.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "pass", "1")
    return bool(value) if value is not None else False


def _extract_float(data: dict, key: str, default: float = 0.0) -> float:
    value = data.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
