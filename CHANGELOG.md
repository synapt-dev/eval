# Changelog

## v0.1.0 (2026-05-07)

Initial release of @synapt/eval.

### Components

- **Phase 1.1**: Project scaffolding, core types (`Fixture`, `EvalResult`, `CategoryMetrics`), scoring primitives (Precision@K, Recall@K, Kendall's Tau), adapter ABCs
- **Phase 1.2**: Eval runner (retrieval, generation, edge case), orchestration (`RunEnvelope`, `compute_deltas`, `pr_gate`), `GateResult` for L1 PR gating
- **Phase 1.3**: Reviewer SDK (`Reviewer`, `Predicate`, `FrameworkReviewer`, `ReviewerChain`), LLM judge integration (`JudgingReviewer`, `OpenAIJudge`, `AnthropicJudge`), judge response parsing
- **Phase 1.4**: Suggestion engine with 10 baseline rules (retrieval, generation, cross-cutting, trending), `@suggestion_rule` decorator pattern, `SuggestionEngine.with_defaults()`
- **Phase 1.5**: Report card generator (markdown + JSON), `compose_report_card()` pure data assembly, schema v1.0 for Pro dashboard compatibility
- **Phase 1.6**: Self-hosted trending (`TrendingStore`, `compute_trending_deltas()`), CLI viewer (`synapt-eval trending`) with text/markdown/json output, TTY-aware formatting
- **Phase 1.7**: PR-gate GitHub Actions adapter (composite action), sticky PR comment, configurable `fail-on` level, `action.yml` at repo root for `uses: synapt-dev/eval@v0.1.0`
- **Phase 1.8**: Documentation (6 guides), runnable examples (3 pipelines), CHANGELOG, README polish

### Stats

- 225+ tests
- Zero external dependencies (judges optional via extras)
- Python 3.10+
