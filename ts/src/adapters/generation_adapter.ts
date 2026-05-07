export interface GenerationOutput {
  text: string;
  latencyMs: number;
  metadata?: Record<string, unknown>;
}

export interface GenerationAdapter {
  generate(query: string, context?: unknown[]): Promise<GenerationOutput>;
}
