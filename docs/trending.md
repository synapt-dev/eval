# Trending

Self-hosted eval history with a CLI viewer. Track metric changes across runs without external services.

## How it works

`TrendingStore` saves report card JSON files to a directory. Each run produces one file named `run-{run_id}.json`. The CLI reads these files and displays metric history with delta indicators.

## Saving history

```python
from synapt_eval.trending import TrendingStore
from synapt_eval.report_card import compose_report_card

card = compose_report_card(results, run_id="2024-01-15")
store = TrendingStore(".synapt-eval/history")
store.save(card)
```

## CLI viewer

```bash
# Text output (default)
synapt-eval trending --path .synapt-eval/history

# Markdown table
synapt-eval trending --format markdown

# JSON for piping
synapt-eval trending --format json | jq '.[0]'

# Limit to recent runs
synapt-eval trending --limit 5
```

### Text output

When running in a terminal, the CLI uses ASCII arrows for metric deltas:

```
Eval Trending
============================================================

Run: 2024-01-15  Status: PASS
  retrieval: p_at_5=0.850^, r_at_10=0.720^

Run: 2024-01-14  Status: PASS
  retrieval: p_at_5=0.800, r_at_10=0.700
```

When piped (e.g., `synapt-eval trending | grep retrieval`), arrows are replaced with words: `(up)`, `(down)`, `(flat)`.

### Markdown output

```markdown
# Eval Trending

## retrieval

| Run | P@5 | R@10 | Tau | Status |
|-----|-----|------|-----|--------|
| 2024-01-15 | 0.850 | 0.720 | - | PASS |
| 2024-01-14 | 0.800 | 0.700 | - | PASS |
```

## Delta computation

`compute_trending_deltas()` compares the two most recent runs:

```python
from synapt_eval.trending import compute_trending_deltas

history = store.load_history()
deltas = compute_trending_deltas(history)
for d in deltas:
    print(f"{d['category']}/{d['metric']}: {d['direction']} ({d['delta']:+.3f})")
```

Each delta contains:

| Field | Type | Description |
|-------|------|-------------|
| `category` | str | Eval category |
| `metric` | str | Metric name (p_at_5, r_at_10, tau) |
| `current` | float | Latest value |
| `previous` | float | Previous value |
| `delta` | float | Numeric change |
| `direction` | str | `up`, `down`, or `flat` |

## CI integration

Use the GitHub Action's `trending-path` input to accumulate history:

```yaml
- uses: synapt-dev/eval@v0.1.0
  with:
    results-path: results.json
    trending-path: .synapt-eval/history
```

Commit the history directory to your repo to track trends across PRs. The `MonotonicDegradationRule` and `StableLowRule` suggestion rules consume this history to flag sustained declines.

## Listing runs

```python
store = TrendingStore(".synapt-eval/history")
runs = store.list_runs()  # Returns list of run IDs
```

## Storage format

Each file in the history directory is a JSON report card (schema v1.0). Files are sorted by name (which embeds the run ID/timestamp) for chronological ordering. Corrupted files are silently skipped during load.
