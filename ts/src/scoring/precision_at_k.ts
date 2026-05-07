export function precisionAtK(
  retrieved: string[],
  relevant: string[],
  k: number = 5,
): number {
  if (k <= 0) return 0;
  const topK = retrieved.slice(0, k);
  if (topK.length === 0) return 0;
  const relevantSet = new Set(relevant);
  const hits = topK.filter((item) => relevantSet.has(item)).length;
  return hits / topK.length;
}
