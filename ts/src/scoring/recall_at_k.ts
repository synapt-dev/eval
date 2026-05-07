export function recallAtK(
  retrieved: string[],
  relevant: string[],
  k: number = 10,
): number {
  if (relevant.length === 0 || k <= 0) return 0;
  const topK = retrieved.slice(0, k);
  const relevantSet = new Set(relevant);
  const hits = topK.filter((item) => relevantSet.has(item)).length;
  return hits / relevantSet.size;
}
