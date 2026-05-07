# @synapt/eval

[![PyPI](https://img.shields.io/pypi/v/synapt-eval)](https://pypi.org/project/synapt-eval/)
[![Python](https://img.shields.io/pypi/pyversions/synapt-eval)](https://pypi.org/project/synapt-eval/)
[![License](https://img.shields.io/github/license/synapt-dev/eval)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/synapt-dev/eval/ci.yml?label=CI)](https://github.com/synapt-dev/eval/actions)

Domain-agnostic eval framework for AI applications. Measure retrieval quality, generation accuracy, and policy compliance across any vertical.

## Install

```bash
pip install synapt-eval
```

Or install from source:

```bash
pip install git+https://github.com/synapt-dev/eval.git
```

## Quick Start

```python
import asyncio
from synapt_eval import Fixture, EvalResult, CategoryMetrics
from synapt_eval.adapters import RetrievalAdapter, RetrievalCandidate
from synapt_eval.scoring import precision_at_k, recall_at_k
from synapt_eval.report_card import compose_report_card, generate_markdown

class MyRetrieval(RetrievalAdapter):
    async def retrieve(self, query: str, k: int = 10) -> list[RetrievalCandidate]:
        # Connect your vector store here
        return [RetrievalCandidate(id="doc1", score=0.95)]

# Run eval and generate report
results = [EvalResult(
    category="retrieval",
    metrics=CategoryMetrics(p_at_5=0.85, r_at_10=0.72, n=50),
)]
card = compose_report_card(results, run_id="my-first-eval")
print(generate_markdown(card))
```

See [docs/quickstart.md](docs/quickstart.md) for a complete walkthrough and [examples/](examples/) for runnable code.

## Architecture

synapt-eval separates the **eval framework** (scoring, review, reporting) from **domain-specific adapters** (your retrieval backend, your generation pipeline, your fixtures).

```
Layer              Module                      Purpose
-------            ------                      -------
Types              synapt_eval.types           Core data types (Fixture, EvalResult, CategoryMetrics)
Scoring            synapt_eval.scoring         Precision@K, Recall@K, Kendall's Tau
Adapters           synapt_eval.adapters        Customer-facing ABCs (Retrieval, Generation, Judge, Fixture)
Runner             synapt_eval.runner          Eval execution, orchestration, PR gate
Reviewer           synapt_eval.reviewer        Verdict framework, predicate chains, LLM judge bridge
Suggestion Engine  synapt_eval.suggestion_engine  Rule-based actionable recommendations
Report Card        synapt_eval.report_card     Markdown + JSON report generation
Trending           synapt_eval.trending        Self-hosted JSON history store + delta computation
CLI                synapt_eval.cli             Command-line viewer (synapt-eval trending)
Actions            synapt_eval.actions         GitHub Actions PR-gate adapter
```

## Features

| Feature | Description |
|---------|-------------|
| **Scoring primitives** | Precision@K, Recall@K, Kendall's Tau rank correlation |
| **Adapter pattern** | Plug in any retrieval/generation backend via ABCs |
| **Reviewer SDK** | Composable predicate chains + LLM judge integration |
| **Suggestion engine** | 10 baseline rules with decorator pattern for custom rules |
| **Report card** | Markdown + JSON output with schema versioning |
| **PR gate** | Regression detection with configurable thresholds |
| **Trending** | Self-hosted history store with CLI viewer |
| **GitHub Action** | `uses: synapt-dev/eval@v0.1.0` for CI integration |

## GitHub Action

Add eval gating to your PR workflow:

```yaml
- name: Run eval
  run: python my_eval_script.py --output results.json

- name: PR Gate
  uses: synapt-dev/eval@v0.1.0
  with:
    results-path: results.json
    baseline-path: baseline.json
    threshold: "0.05"
    fail-on: error
```

The action posts a report card comment on the PR and fails the workflow on regressions. See [docs/pr-gate.md](docs/pr-gate.md) for full configuration.

## CLI

```bash
# View eval trending history
synapt-eval trending --path .synapt-eval/history --format text

# Output as markdown or JSON
synapt-eval trending --format markdown
synapt-eval trending --format json --limit 5
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Quickstart](docs/quickstart.md) | End-to-end retrieval eval in 60 lines |
| [Adapter API](docs/adapter-api.md) | Writing custom adapters |
| [Reviewer Framework](docs/reviewer-framework.md) | Custom reviewers + judge integration |
| [PR Gate](docs/pr-gate.md) | GitHub Actions CI integration |
| [Suggestions](docs/suggestions.md) | Writing custom suggestion rules |
| [Trending](docs/trending.md) | Self-hosted trending CLI |

## Examples

Runnable examples in [examples/](examples/):

- **[retrieval-eval](examples/retrieval-eval/)** -- mock retrieval backend + fixtures + report card
- **[generation-eval](examples/generation-eval/)** -- mock generation pipeline + judge
- **[full-pipeline](examples/full-pipeline/)** -- combined retrieval + generation + reviewer + suggestions

## Pro Tier

Want vertical-specific eval packs, a hosted dashboard, or SOC2 attestations? Visit [synapt.dev](https://synapt.dev) for synapt-eval Pro.

## License

MIT
