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
}
