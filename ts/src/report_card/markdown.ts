import type { Suggestion } from "../suggestion_engine/types.ts";
import type {
  CategorySection,
  ReportCard,
  ReportCardFooter,
  ReportCardHeader,
  TrendingEntry,
} from "./types.ts";

export function generateMarkdown(reportCard: ReportCard): string {
  const parts: string[] = [];

  parts.push(renderHeader(reportCard.header));

  for (const section of reportCard.sections) {
    parts.push(renderSection(section));
  }

  if (reportCard.trending.length > 0) {
    parts.push(renderTrending(reportCard.trending));
  }

  if (reportCard.suggestions.length > 0) {
    parts.push(renderSuggestions(reportCard.suggestions));
  }

  parts.push(renderFooter(reportCard.footer));

  return parts.join("\n");
}

function renderHeader(header: ReportCardHeader): string {
  const lines = ["# Eval Report Card", ""];
  lines.push(`**Run ID**: ${header.runId}  `);
  lines.push(`**Timestamp**: ${header.timestamp}  `);
  if (header.commit) {
    lines.push(`**Commit**: ${header.commit}  `);
  }
  lines.push(
    `**Fixtures**: ${header.fixtureCount} across ${header.categoryCount} categories  `,
  );

  const severityParts: string[] = [];
  for (const level of ["error", "warning", "info"]) {
    const count = header.severityCounts[level] ?? 0;
    if (count > 0) {
      severityParts.push(`${count} ${level.toUpperCase()}`);
    }
  }
  if (severityParts.length > 0) {
    lines.push(`**Severity**: ${severityParts.join(" / ")}`);
  }

  lines.push("", "---", "");
  return lines.join("\n");
}

function renderSection(section: CategorySection): string {
  const lines = [`## ${section.category}`, ""];
  lines.push("| Metric | Value |");
  lines.push("|--------|-------|");
  lines.push(`| P@5 | ${section.metrics.pAt5.toFixed(3)} |`);
  lines.push(`| R@10 | ${section.metrics.rAt10.toFixed(3)} |`);
  if (section.metrics.tau != null) {
    lines.push(`| Tau | ${section.metrics.tau.toFixed(3)} |`);
  }
  lines.push(`| N | ${section.metrics.n} |`);
  lines.push("");

  if (section.suggestions.length > 0) {
    lines.push("### Suggestions", "");
    for (const s of section.suggestions) {
      const level = s.severity.level.toUpperCase();
      lines.push(`- [${level}] **${s.ruleName}**: ${s.message}`);
      if (s.fixHint) {
        lines.push(`  - *Fix*: ${s.fixHint}`);
      }
    }
    lines.push("");
  }

  lines.push("---", "");
  return lines.join("\n");
}

function renderTrending(entries: TrendingEntry[]): string {
  if (entries.length === 0) return "";

  const categories = [...new Set(entries.map((e) => e.category))].sort();
  const lines = ["## Trending", ""];

  for (const category of categories) {
    const catEntries = entries.filter((e) => e.category === category);
    if (catEntries.length === 0) continue;

    lines.push(`### ${category}`, "");

    const metricNames = [
      ...new Set(catEntries.flatMap((e) => Object.keys(e.metrics))),
    ].sort();
    const headerCols = ["Run", ...metricNames.map((m) => m.toUpperCase())];
    lines.push("| " + headerCols.join(" | ") + " |");
    lines.push("| " + headerCols.map(() => "---").join(" | ") + " |");

    for (const entry of catEntries) {
      const row = [entry.runId];
      for (const m of metricNames) {
        const val = entry.metrics[m];
        row.push(val != null ? val.toFixed(3) : "-");
      }
      lines.push("| " + row.join(" | ") + " |");
    }
    lines.push("");
  }

  lines.push("---", "");
  return lines.join("\n");
}

function renderSuggestions(suggestions: Suggestion[]): string {
  const lines = ["## Suggestions Summary", ""];
  lines.push("| # | Severity | Rule | Category | Message |");
  lines.push("|---|----------|------|----------|---------|");

  for (let i = 0; i < suggestions.length; i++) {
    const s = suggestions[i];
    const level = s.severity.level.toUpperCase();
    const category = s.category ?? "-";
    lines.push(
      `| ${i + 1} | ${level} | ${s.ruleName} | ${category} | ${s.message} |`,
    );
  }

  lines.push("", "---", "");
  return lines.join("\n");
}

function renderFooter(footer: ReportCardFooter): string {
  const lines = ["## Result", ""];

  const status = footer.passed ? "PASSED" : "FAILED";
  const parts: string[] = [];
  if (footer.regressionSummary) {
    parts.push(footer.regressionSummary);
  }
  if (footer.totalSuggestions > 0) {
    parts.push(`${footer.totalSuggestions} suggestion(s) for improvement`);
  } else {
    parts.push("No suggestions");
  }

  const detail = parts.length > 0 ? parts.join(". ") + "." : "";
  lines.push(`**${status}** -- ${detail}`);

  if (footer.deltas.length > 0) {
    lines.push("", "### Regression Deltas", "");
    lines.push("| Category | Metric | Baseline | Current | Delta |");
    lines.push("|----------|--------|----------|---------|-------|");
    for (const d of footer.deltas) {
      const flag = d.regression ? " [REGRESSION]" : "";
      const sign = d.delta >= 0 ? "+" : "";
      lines.push(
        `| ${d.category} | ${d.metric} | ${d.baseline.toFixed(3)} | ${d.current.toFixed(3)} | ${sign}${d.delta.toFixed(3)}${flag} |`,
      );
    }
    lines.push("");
  }

  lines.push("");
  return lines.join("\n");
}
