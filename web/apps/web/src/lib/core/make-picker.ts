import { AnswerConfig, defaultPick } from "./answer-config";

export type Picker = (idx: number, n: number) => number;

/** Equivalent of random.choices(range(n), weights=..., k=1). */
function weightedChoice(
  n: number,
  weights: number[],
  rng: () => number,
): number {
  let total = 0;
  for (let i = 0; i < n; i++) total += weights[i] ?? 0;
  if (total <= 0) return defaultPick(n, rng);

  let threshold = rng() * total;
  for (let i = 0; i < n; i++) {
    threshold -= weights[i] ?? 0;
    if (threshold < 0) return i;
  }
  return n - 1;
}

/**
 * Build pick(unitIndex, nOptions) -> option index for smartFill.
 *
 * Falls back to the legacy default on any defect (bad config, unusable
 * weights, out-of-range result) so a misconfiguration can never abort a run.
 */
export function makePicker(
  config: AnswerConfig,
  rng: () => number = Math.random,
): Picker {
  return function pick(idx: number, n: number): number {
    if (n <= 0) return 0;

    let resolved;
    try {
      resolved = config.resolve(idx, n);
    } catch {
      return defaultPick(n, rng);
    }

    if (resolved.kind === "weighted" && resolved.weights) {
      try {
        const chosen = weightedChoice(n, resolved.weights, rng);
        if (Number.isInteger(chosen) && chosen >= 0 && chosen < n) {
          return chosen;
        }
        return defaultPick(n, rng);
      } catch {
        return defaultPick(n, rng);
      }
    }

    if (resolved.kind === "uniform") {
      const chosen = Math.floor(rng() * n);
      return chosen >= 0 && chosen < n ? chosen : defaultPick(n, rng);
    }

    return defaultPick(n, rng);
  };
}