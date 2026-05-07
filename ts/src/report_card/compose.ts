import type { EvalResult } from "../types.ts";
import type { Suggestion } from "../suggestion_engine/types.ts";
import type {
  CategorySection,
  Delta,
  ReportCard,
  ReportCardFooter,
  ReportCardHeader,
  TrendingEntry,
} from "./types.ts";

export interface ComposeOptions {
  results: EvalResult[];
  suggestions?: Suggestion[];
  baseline?: EvalResult[];
  history?: EvalResult[];
  runId?: string;
  timestamp?: string;
  commit?: string;
  config?: Record<string, unknown>;
}

export function composeReportCard(options: ComposeOptions): ReportCard {
  const suggestions = options.suggestions ?? [];
  const now = new Date();
  const runId = options.runId ?? now.toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
  const timestamp = options.timestamp ?? now.toISOString();

  const severityCounts = countSeverities(suggestions);
  const fixtureCount = options.results.reduce((sum, r) => sum + r.metrics.n, 0);

  const header: ReportCardHeader = {
    runId,
    timestamp,
    fixtureCount,
    categoryCount: options.results.length,
    severityCounts,
    commit: options.commit,
    config: options.config ?? {},
  };

  const suggestionByCategory = new Map<string, Suggestion[]>();
  for (const s of suggestions) {
    const cat = s.category ?? "_global";
    const list = suggestionByCategory.get(cat) ?? [];
    list.push(s);
    suggestionByCategory.set(cat, list);
  }

  const sections: CategorySection[] = options.results.map((r) => ({
    category: r.category,
    metrics: r.metrics,
    suggestions: suggestionByCategory.get(r.category) ?? [],
    fixtureCount: r.metrics.n,
  }));

  let deltas: Delta[] = [];
  let regressionSummary: string | undefined;
  if (options.baseline) {
    deltas = computeDeltas(options.results, options.baseline);
    const regressions = deltas.filter((d) => d.regression);
    if (regressions.length > 0) {
      regressionSummary = `${regressions.length} regression(s) detected`;
    }
  }

  const hasErrors = (severityCounts["error"] ?? 0) > 0;
  const hasRegressions = regressionSummary !== undefined;
  const passed = !hasErrors && !hasRegressions;

  const footer: ReportCardFooter = {
    passed,
    totalSuggestions: suggestions.length,
    errorCount: severityCounts["error"] ?? 0,
    warningCount: severityCounts["warning"] ?? 0,
    infoCount: severityCounts["info"] ?? 0,
    regressionSummary,
    deltas,
  };

  const trending = options.history ? buildTrending(options.history) : [];

  return { header, sections, suggestions, footer, trending };
}

function countSeverities(suggestions: Suggestion[]): Record<string, number> {
  const counts: Record<string, number> = { error: 0, warning: 0, info: 0 };
  for (const s of suggestions) {
    const level = s.severity.level;
    if (level in counts) {
      counts[level]++;
    } else if (s.severity.weight >= 0.75) {
      counts["error"]++;
    } else if (s.severity.weight >= 0.5) {
      counts["warning"]++;
    } else {
      counts["info"]++;
    }
  }
  return counts;
}

function computeDeltas(
  results: EvalResult[],
  baseline: EvalResult[],
  threshold = 0.05,
): Delta[] {
  const deltas: Delta[] = [];
  for (const result of results) {
    const base = baseline.find((b) => b.category === result.category);
    if (!base) continue;

    const metrics: Array<{ key: "pAt5" | "rAt10"; name: string }> = [
      { key: "pAt5", name: "p_at_5" },
      { key: "rAt10", name: "r_at_10" },
    ];

    for (const { key, name } of metrics) {
      const current = result.metrics[key];
      const baseVal = base.metrics[key];
      const delta = current - baseVal;
      deltas.push({
        category: result.category,
        metric: name,
        baseline: baseVal,
        current,
        delta,
        regression: delta < -threshold,
      });
    }
  }
  return deltas;
}

function buildTrending(history: EvalResult[]): TrendingEntry[] {
  return history.map((r) => {
    const metrics: Record<string, number> = {
      p_at_5: r.metrics.pAt5,
      r_at_10: r.metrics.rAt10,
    };
    if (r.metrics.tau != null) {
      metrics["tau"] = r.metrics.tau;
    }
    return { runId: "historical", category: r.category, metrics };
  });
}
