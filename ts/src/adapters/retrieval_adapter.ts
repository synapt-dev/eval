export interface RetrievalCandidate {
  id: string;
  score: number;
}

export interface RetrievalAdapter {
  retrieve(query: string, k?: number): Promise<RetrievalCandidate[]>;
  embed?(text: string): Promise<number[]>;
}
