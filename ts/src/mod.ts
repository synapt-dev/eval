export type {
  EvalConfig,
  Fixture,
  CategoryMetrics,
  PerFixtureResult,
  RetrievalResult,
  GenerationResult,
  EdgeCaseFixture,
  EdgeCaseResult,
  EvalResult,
} from "./types.ts";

export { precisionAtK, recallAtK, kendallTau } from "./scoring/mod.ts";

export type {
  RetrievalAdapter,
  RetrievalCandidate,
  GenerationAdapter,
  GenerationOutput,
  JudgeAdapter,
  JudgeRequest,
  JudgeResponse,
  FixtureLoader,
} from "./adapters/mod.ts";

export {
  SEVERITY_INFO,
  SEVERITY_WARNING,
  SEVERITY_ERROR,
  SEVERITY_CRITICAL,
  type Severity,
  type CheckResult,
  type Verdict,
  type Reviewer,
  type Predicate,
  FrameworkReviewer,
  ReviewerChain,
  type ChainStrategy,
} from "./reviewer/mod.ts";

export {
  type Suggestion,
  type SuggestionRule,
  suggestionRule,
  SuggestionEngine,
  LowPrecisionRule,
  LowRecallRule,
  HighNoResultsRule,
  LowSuccessRateRule,
  HallucinationSignalRule,
  VerdictFailureRule,
  RegressionRule,
  CategoryImbalanceRule,
  MonotonicDegradationRule,
  StableLowRule,
  defaultRules,
} from "./suggestion_engine/mod.ts";

export {
  type ReportCard,
  type ReportCardHeader,
  type CategorySection,
  type ReportCardFooter,
  type TrendingEntry,
  type Delta,
  type ComposeOptions,
  composeReportCard,
  generateMarkdown,
} from "./report_card/mod.ts";
