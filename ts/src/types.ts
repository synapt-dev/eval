export interface EvalConfig {
  fixturesPath: string;
  outputPath: string;
  categories: string[];
  embeddingModel?: string;
  generationModel?: string;
  apiEndpoints?: Record<string, string>;
}

export interface Fixture<T = unknown> {
  id: string;
  category: string;
  query: string;
  expected: string[];
  userHistory?: T[];
  metadata?: Record<string, unknown>;
}

export interface CategoryMetrics {
  pAt5: number;
  rAt10: number;
  tau?: number;
  n: number;
}

export interface PerFixtureResult {
  fixtureId: string;
  category: string;
  passed: boolean;
  score: number;
  details?: Record<string, unknown>;
}

export interface RetrievalResult {
  fixtureId: string;
  retrievedIds: string[];
  scores: number[];
  pAt5: number;
  rAt10: number;
  tau?: number;
}

export interface GenerationResult {
  fixtureId: string;
  query: string;
  output: string;
  latencyMs: number;
  status: string;
}

export interface EdgeCaseFixture {
  id: string;
  category: string;
  inputText: string;
  expectedBehavior: "block" | "allow" | "flag";
  notes?: string;
}

export interface EdgeCaseResult {
  id: string;
  category: string;
  expected: string;
  actual: string;
  passed: boolean;
  notes?: string;
}

export interface EvalResult {
  category: string;
  metrics: CategoryMetrics;
  perFixture?: PerFixtureResult[];
  runMetrics?: RunMetrics;
}

/** Portable measurement keys match the JSON report schema. Prompt includes cache subsets. */
export interface TokenCount {
  value: number | null;
  status: "measured" | "unavailable";
}

export interface TokenUsage {
  prompt_tokens: TokenCount;
  cached_prompt_tokens: TokenCount;
  cache_write_tokens: TokenCount;
  completion_tokens: TokenCount;
  total_tokens: TokenCount;
}

export interface RunCost {
  value_usd: number | null;
  status: "measured" | "GUESS" | "unavailable";
  source?: string | null;
  reason?: string | null;
  rates?: Record<string, unknown> | null;
}

export interface RunMetrics {
  runtime?: string | null;
  runtime_versions?: string[];
  models?: string[];
  usage: TokenUsage;
  turns?: number | null;
  tool_calls?: number | null;
  wall_seconds?: number | null;
  box_minutes?: number | null;
  model_cost: RunCost;
  box_cost: RunCost;
  scope?: string | null;
  start?: string | null;
  end?: string | null;
  counting_rule?: string | null;
  usage_basis?: string | null;
  wall_basis?: string | null;
}
