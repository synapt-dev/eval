export type { Suggestion } from "./types.ts";
export type { SuggestionRule } from "./protocol.ts";
export { suggestionRule } from "./protocol.ts";
export { SuggestionEngine } from "./engine.ts";
export {
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
} from "./rules/mod.ts";
