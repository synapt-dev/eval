export interface Severity {
  readonly level: string;
  readonly weight: number;
}

export const SEVERITY_INFO: Severity = { level: "info", weight: 0.25 };
export const SEVERITY_WARNING: Severity = { level: "warning", weight: 0.5 };
export const SEVERITY_ERROR: Severity = { level: "error", weight: 0.75 };
export const SEVERITY_CRITICAL: Severity = { level: "critical", weight: 1.0 };

export interface CheckResult {
  name: string;
  passed: boolean;
  severity: Severity;
  reasoning?: string;
}

export interface Verdict {
  passed: boolean;
  reasoning: string;
  severity: Severity;
  checks: CheckResult[];
  score: number;
}
