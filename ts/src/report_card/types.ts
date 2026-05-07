import type { CategoryMetrics } from "../types.ts";
import type { Suggestion } from "../suggestion_engine/types.ts";

export interface ReportCardHeader {
  runId: string;
  timestamp: string;
  fixtureCount: number;
  categoryCount: number;
  severityCounts: Record<string, number>;
  commit?: string;
  config?: Record<string, unknown>;
}

export interface CategorySection {
  category: string;
  metrics: CategoryMetrics;
  suggestions: Suggestion[];
  fixtureCount: number;
}

export interface Delta {
  category: string;
  metric: string;
  baseline: number;
  current: number;
  delta: number;
  regression: boolean;
}

export interface ReportCardFooter {
  passed: boolean;
  totalSuggestions: number;
  errorCount: number;
  warningCount: number;
  infoCount: number;
  regressionSummary?: string;
  deltas: Delta[];
}

export interface TrendingEntry {
  runId: string;
  category: string;
  metrics: Record<string, number>;
}

export interface ReportCard {
  header: ReportCardHeader;
  sections: CategorySection[];
  suggestions: Suggestion[];
  footer: ReportCardFooter;
  trending: TrendingEntry[];
}
