# Reviewer Framework

The reviewer framework produces verdicts (pass/fail with scores) from individual outputs. It supports both rule-based predicates and LLM judge integration, composable via chains.

## Core concepts

| Concept | Class | Description |
|---------|-------|-------------|
| **Reviewer** | `Reviewer` (ABC) | Produces a `Verdict` from an output/expected/query triple |
| **Predicate** | `Predicate` (ABC) | A single check that returns `CheckResult` |
| **FrameworkReviewer** | `FrameworkReviewer` | Chains predicates into a single reviewer |
| **ReviewerChain** | `ReviewerChain` | Composes multiple reviewers with conflict resolution |
| **JudgingReviewer** | `JudgingReviewer` | Bridges `JudgeAdapter` into the reviewer protocol |

## Writing a predicate

Predicates check a single output against expectations:

```python
from synapt_eval.reviewer import Predicate, CheckResult, SEVERITY_ERROR


class KeywordCheck(Predicate):
    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        missing = [kw for kw in expected if kw.lower() not in output.lower()]
        if missing:
            return CheckResult(
                name="keyword_check",
                passed=False,
                severity=SEVERITY_ERROR,
                reasoning=f"Missing: {', '.join(missing)}",
            )
        return CheckResult(
            name="keyword_check",
            passed=True,
            severity=SEVERITY_ERROR,
            reasoning="All keywords found",
        )
```

### CheckResult fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Identifier for this check |
| `passed` | bool | Whether the check passed |
| `severity` | Severity | How serious a failure is |
| `reasoning` | str | Human-readable explanation |

## Building a FrameworkReviewer

Compose predicates into a single reviewer:

```python
from synapt_eval.reviewer import FrameworkReviewer

reviewer = FrameworkReviewer(predicates=[
    KeywordCheck(),
    MinLengthCheck(min_length=50),
])

verdict = await reviewer.review(
    output="Python is a programming language.",
    expected=["programming", "language"],
    query="What is Python?",
)
print(f"Passed: {verdict.passed}, Score: {verdict.score:.2f}")
```

The `FrameworkReviewer` fails if ANY predicate fails. The severity of the verdict is the worst severity among failures.

## Severity levels

| Level | Weight | Meaning |
|-------|--------|---------|
| `SEVERITY_INFO` | 0.25 | Informational, never fails |
| `SEVERITY_WARNING` | 0.50 | Potential issue, configurable fail threshold |
| `SEVERITY_ERROR` | 0.75 | Significant issue, fails by default |
| `SEVERITY_CRITICAL` | 1.00 | Blocking issue, always fails |

## ReviewerChain

Compose multiple reviewers with conflict resolution:

```python
from synapt_eval.reviewer import ReviewerChain

chain = ReviewerChain(
    reviewers=[predicate_reviewer, judge_reviewer],
    strategy="weighted",  # "strictest", "majority", or "weighted"
)

verdict = await chain.review(
    output="some text", expected=["expected"], query="query"
)
```

### Strategies

| Strategy | Behavior |
|----------|----------|
| `strictest` | Fails if ANY reviewer fails (AND logic) |
| `majority` | Passes if >50% of reviewers pass |
| `weighted` | Weighted average of scores using severity weights; passes if >= 0.5 |

## LLM Judge integration

Bridge a `JudgeAdapter` into the reviewer protocol:

```python
from synapt_eval.reviewer import JudgingReviewer
from synapt_eval.judges.openai import OpenAIJudge

judge = OpenAIJudge(model="gpt-4o-mini")
judge_reviewer = JudgingReviewer(judge=judge)

verdict = await judge_reviewer.review(
    output="Generated text here",
    expected=["relevant", "accurate"],
    query="What is X?",
)
```

### Built-in judges

```python
# OpenAI (requires: pip install synapt-eval[openai])
from synapt_eval.judges.openai import OpenAIJudge
judge = OpenAIJudge(model="gpt-4o-mini")

# Anthropic (requires: pip install synapt-eval[anthropic])
from synapt_eval.judges.anthropic import AnthropicJudge
judge = AnthropicJudge(model="claude-haiku-4-5-20251001")
```

### Ensemble judging

Achieve ensemble judging by putting multiple `JudgingReviewer` instances in a `ReviewerChain`:

```python
chain = ReviewerChain(
    reviewers=[
        JudgingReviewer(judge=OpenAIJudge("gpt-4o-mini")),
        JudgingReviewer(judge=AnthropicJudge("claude-haiku-4-5-20251001")),
    ],
    strategy="majority",
)
```

## Next steps

- [Adapter API](adapter-api.md): writing the `JudgeAdapter` interface
- [Suggestions](suggestions.md): turn reviewer verdicts into actionable recommendations
