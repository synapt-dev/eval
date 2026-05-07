"""OpenAI judge reference implementation."""

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


class OpenAIJudge(JudgeAdapter):
    """LLM-as-judge using OpenAI's chat completions API.

    Requires: pip install synapt-eval[openai]
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        prompt_template: str | None = None,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError("OpenAI SDK required: pip install synapt-eval[openai]") from exc

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._prompt_template = prompt_template or _DEFAULT_PROMPT

    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        prompt = self._build_prompt(request)
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return parse_judge_json(content)

    def _build_prompt(self, request: JudgeRequest) -> str:
        rubric_section = f"Evaluation criteria: {request.rubric}" if request.rubric else ""
        return self._prompt_template.format(
            query=request.query,
            expected=", ".join(request.expected),
            actual=request.actual,
            rubric_section=rubric_section,
        )
