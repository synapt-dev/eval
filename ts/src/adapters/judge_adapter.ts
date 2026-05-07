export interface JudgeRequest {
  query: string;
  expected: string[];
  actual: string;
  rubric?: string;
  context?: Record<string, unknown>;
}

export interface JudgeResponse {
  passed: boolean;
  score: number;
  reasoning: string;
  raw?: Record<string, unknown>;
}

export interface JudgeAdapter {
  judge(request: JudgeRequest): Promise<JudgeResponse>;
}
