export {
  LowPrecisionRule,
  LowRecallRule,
  HighNoResultsRule,
} from "./retrieval.ts";
export {
  LowSuccessRateRule,
  HallucinationSignalRule,
  VerdictFailureRule,
} from "./generation.ts";
export { RegressionRule, CategoryImbalanceRule } from "./cross_cutting.ts";
export { MonotonicDegradationRule, StableLowRule } from "./trending.ts";

import { LowPrecisionRule, LowRecallRule, HighNoResultsRule } from "./retrieval.ts";
import { LowSuccessRateRule, HallucinationSignalRule, VerdictFailureRule } from "./generation.ts";
import { RegressionRule, CategoryImbalanceRule } from "./cross_cutting.ts";
import { MonotonicDegradationRule, StableLowRule } from "./trending.ts";
import type { SuggestionRule } from "../protocol.ts";

export function defaultRules(): SuggestionRule[] {
  return [
    new LowPrecisionRule(),
    new LowRecallRule(),
    new HighNoResultsRule(),
    new LowSuccessRateRule(),
    new HallucinationSignalRule(),
    new VerdictFailureRule(),
    new RegressionRule(),
    new CategoryImbalanceRule(),
    new MonotonicDegradationRule(),
    new StableLowRule(),
  ];
}
