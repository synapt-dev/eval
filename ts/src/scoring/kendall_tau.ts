export function kendallTau(
  rankingA: string[],
  rankingB: string[],
): number | null {
  const bSet = new Set(rankingB);
  const common = rankingA.filter((x) => bSet.has(x));
  const n = common.length;
  if (n < 2) return null;

  const rankB = new Map<string, number>();
  for (let i = 0; i < rankingB.length; i++) {
    rankB.set(rankingB[i], i);
  }
  const ordered = common.map((item) => rankB.get(item)!);

  let concordant = 0;
  let discordant = 0;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (ordered[i] < ordered[j]) concordant++;
      else if (ordered[i] > ordered[j]) discordant++;
    }
  }

  const pairs = (n * (n - 1)) / 2;
  if (pairs === 0) return null;
  return (concordant - discordant) / pairs;
}
