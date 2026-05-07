# PR Gate GitHub Action

The synapt-eval GitHub Action runs regression detection on eval results and posts a report card to your PR.

## Basic usage

```yaml
name: Eval Gate
on: pull_request

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install and run eval
        run: |
          pip install synapt-eval
          python my_eval_script.py --output results.json

      - name: PR Gate
        uses: synapt-dev/eval@v0.1.0
        with:
          results-path: results.json
          baseline-path: baseline.json
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `results-path` | yes | - | Path to eval results JSON file |
| `baseline-path` | no | - | Path to baseline results for regression detection |
| `threshold` | no | `0.05` | Regression threshold (metrics must not drop by more than this) |
| `fail-on` | no | `error` | Severity level that fails the workflow: `error`, `warning`, or `none` |
| `comment` | no | `true` | Post/update a report card comment on the PR |
| `trending-path` | no | - | Path to trending history directory |
| `python-version` | no | `3.12` | Python version for the runner |

## Outputs

| Output | Description |
|--------|-------------|
| `passed` | Whether the gate passed (`true`/`false`) |
| `report-json` | Path to the report card JSON file |
| `report-markdown` | Report card as a markdown string |

## Results JSON format

The action accepts results as a JSON file. Two formats are supported:

### Object format (recommended)

```json
{
  "results": [
    {
      "category": "retrieval",
      "metrics": { "p_at_5": 0.85, "r_at_10": 0.72, "n": 50 },
      "per_fixture": []
    }
  ]
}
```

### Array format

```json
[
  {
    "category": "retrieval",
    "metrics": { "p_at_5": 0.85, "r_at_10": 0.72, "n": 50 },
    "per_fixture": []
  }
]
```

## Failure behavior

The action determines pass/fail based on two factors:

1. **Regressions**: if any metric drops below `baseline - threshold`, the action fails regardless of `fail-on` setting.
2. **Severity level**: controlled by the `fail-on` input:
   - `error` (default): fails if any ERROR-severity suggestions exist
   - `warning`: fails if any WARNING or ERROR suggestions exist
   - `none`: only regressions cause failure

## PR comment

The action posts a sticky comment on the PR with the full report card markdown. On subsequent pushes, it updates the existing comment instead of creating a new one.

The comment is identified by a hidden HTML marker (`<!-- synapt-eval-report -->`). If you use multiple eval configurations, they will share the same comment.

To disable comments, set `comment: "false"`.

## Trending

Save eval history across runs by setting `trending-path`:

```yaml
- uses: synapt-dev/eval@v0.1.0
  with:
    results-path: results.json
    trending-path: .synapt-eval/history
```

Each run saves a JSON snapshot to the trending directory. Use the CLI to view history:

```bash
synapt-eval trending --path .synapt-eval/history
```

## Using outputs in downstream steps

```yaml
- name: PR Gate
  id: gate
  uses: synapt-dev/eval@v0.1.0
  with:
    results-path: results.json

- name: Upload report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: eval-report
    path: ${{ steps.gate.outputs.report-json }}
```

## Generating results JSON from your eval script

Your eval script should write results in the format above. Example:

```python
import json
from synapt_eval import EvalResult, CategoryMetrics
from synapt_eval.runner.orchestration import RunEnvelope

results = [EvalResult(
    category="retrieval",
    metrics=CategoryMetrics(p_at_5=0.85, r_at_10=0.72, n=50),
)]

envelope = RunEnvelope.create(results)
envelope.save(".")  # Writes run-{timestamp}.json
```
