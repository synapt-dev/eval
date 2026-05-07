import type { Severity } from "../reviewer/types.ts";

export interface Suggestion {
  severity: Severity;
  message: string;
  ruleName: string;
  metric?: string;
  category?: string;
  fixHint?: string;
}
