"""Anthropic judge reference implementation."""

from __future__ import annotations

from synapt_eval.adapters.judge_adapter import JudgeAdapter, JudgeRequest, JudgeResponse
from synapt_eval.judges.parsing import parse_judge_json

_DEFAULT_PROMPT = """Evaluate the following response. Return JSON with keys:
- "passed" (bool): whether the response meets the criteria
- "score" (float 0.0-1.0): quality score
- "reasoning" (string): brief explanation

Query: {query}
Expected: {expected}
Actual response: {actual}

{rubric_section}

Return ONLY valid JSON."""


class AnthropicJudge(JudgeAdapter):
    """LLM-as-judge using Anthropic's messages API.

    Requires: pip install synapt-eval[anthropic]
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        api_key: str | None = None,
        prompt_template: str | None = None,
        max_tokens: int = 1024,
    ) -> None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise ImportError("Anthropic SDK required: pip install synapt-eval[anthropic]") from exc

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._prompt_template = prompt_template or _DEFAULT_PROMPT
        self._max_tokens = max_tokens

    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        prompt = self._build_prompt(request)
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text if response.content else ""
        return parse_judge_json(content)

    def _build_prompt(self, request: JudgeRequest) -> str:
        rubric_section = f"Evaluation criteria: {request.rubric}" if request.rubric else ""
        return self._prompt_template.format(
            query=request.query,
            expected=", ".join(request.expected),
            actual=request.actual,
            rubric_section=rubric_section,
        )
