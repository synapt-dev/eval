# Adapter API

Adapters are the integration point between synapt-eval and your system. You implement ABCs; the framework handles scoring, aggregation, and reporting.

## RetrievalAdapter

Connect your vector store or search backend:

```python
from synapt_eval.adapters import RetrievalAdapter, RetrievalCandidate


class SupabaseRetrieval(RetrievalAdapter):
    def __init__(self, client, table: str):
        self.client = client
        self.table = table

    async def retrieve(self, query: str, k: int = 10) -> list[RetrievalCandidate]:
        response = await self.client.rpc("match_documents", {
            "query_text": query,
            "match_count": k,
        }).execute()
        return [
            RetrievalCandidate(id=row["id"], score=row["similarity"])
            for row in response.data
        ]
```

### Required methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `retrieve` | `async (query: str, k: int) -> list[RetrievalCandidate]` | Return top-K candidates |

### Optional methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `embed` | `async (text: str) -> list[float]` | Embed text for similarity comparison |

## GenerationAdapter

Connect your LLM pipeline:

```python
from synapt_eval.adapters import GenerationAdapter, GenerationOutput


class MyLLM(GenerationAdapter):
    async def generate(self, query: str, context=None) -> GenerationOutput:
        response = await call_llm(query, context=context)
        return GenerationOutput(
            text=response.text,
            latency_ms=response.latency,
        )
```

### Required methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `generate` | `async (query: str, context: list) -> GenerationOutput` | Generate a response |

## FixtureLoader

Load eval fixtures from any data source. The framework ships `JsonFixtureLoader` for JSONL files:

```python
from synapt_eval.adapters.fixture_loader import JsonFixtureLoader

loader = JsonFixtureLoader("fixtures/")
# Loads fixtures/retrieval.jsonl, fixtures/generation.jsonl, etc.
```

For custom sources, implement the ABC:

```python
from synapt_eval.adapters import FixtureLoader
from synapt_eval import Fixture


class DatabaseFixtureLoader(FixtureLoader):
    async def load(self, category: str) -> list[Fixture]:
        rows = await db.fetch("SELECT * FROM fixtures WHERE category = $1", category)
        return [
            Fixture(id=r["id"], category=category, query=r["query"], expected=r["expected"])
            for r in rows
        ]

    async def setup(self):
        await db.execute("CREATE TEMP TABLE IF NOT EXISTS ...")

    async def cleanup(self):
        await db.execute("DROP TABLE IF EXISTS ...")
```

### Required methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `load` | `async (category: str) -> list[Fixture]` | Load fixtures for a category |

### Optional methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `setup` | `async () -> None` | Set up test state before eval |
| `cleanup` | `async () -> None` | Clean up test state after eval |

## JudgeAdapter

Connect an LLM judge for quality assessment:

```python
from synapt_eval.adapters import JudgeAdapter, JudgeRequest, JudgeResponse


class MyJudge(JudgeAdapter):
    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        prompt = f"Rate this response:\nQuery: {request.query}\nResponse: {request.response}"
        result = await call_llm(prompt)
        return JudgeResponse(
            score=result.score,
            passed=result.score >= 0.7,
            reasoning=result.explanation,
        )
```

See [reviewer-framework.md](reviewer-framework.md) for how to compose judges with predicate-based reviewers.

## JSONL fixture format

Each line is a JSON object:

```json
{"id": "q1", "query": "search query", "expected": ["doc_a", "doc_b"], "metadata": {"source": "manual"}}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique fixture identifier |
| `query` | string | yes | The eval query |
| `expected` | list[string] | yes | Expected result IDs (in order) |
| `category` | string | no | Category override (defaults to filename) |
| `user_history` | list | no | Conversation history for contextual evals |
| `metadata` | object | no | Arbitrary metadata |
