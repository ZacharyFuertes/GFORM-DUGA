import type {
  AnswerConfigData,
  ConfigMode,
  Resolved,
} from "./types.ts";

export const MODES: readonly ConfigMode[] = ["default", "uniform", "weighted"];

/**
 * Selection rule used when nothing has been customised.
 *
 * Kept byte-for-byte equivalent to the original bot behaviour so that an
 * untouched config produces exactly the same runs as before.
 */
export function defaultPick(n: number, rng: () => number = Math.random): number {
  if (n <= 0) return 0;
  if (n === 5) return Math.floor(rng() * 3);
  if (n === 2) return rng() < 0.5 ? 0 : 1;
  return Math.floor(rng() * n);
}

/** Python's round(): half-to-even, so resampling matches the desktop app. */
function pyRound(x: number): number {
  const floor = Math.floor(x);
  const frac = x - floor;
  if (frac > 0.5) return floor + 1;
  if (frac < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

/** Resample a weight list onto n options; null when nothing usable. */
export function fit(weights: number[], n: number): number[] | null {
  if (n <= 0 || !weights.length) return null;

  const cleaned = weights.map((w) => Math.max(0, Number(w) || 0));
  let out: number[];

  if (cleaned.length === n) {
    out = cleaned;
  } else if (n === 1) {
    out = [cleaned[0] as number];
  } else {
    out = Array.from(
      { length: n },
      (_, i) =>
        cleaned[pyRound((i * (cleaned.length - 1)) / (n - 1))] as number,
    );
  }

  // An all-zero result is unusable: weighted choice would raise on it.
  return out.reduce((a, b) => a + b, 0) > 0 ? out : null;
}

function cleanList(values: unknown): number[] {
  if (!values) return [];
  if (!Array.isArray(values)) return [];
  return values.map((value) => {
    const n = Number(value);
    return Number.isFinite(n) ? Math.max(0, n) : 0;
  });
}

/**
 * Global default mode plus per-unit weight overrides.
 *
 * mode:
 *   "default"  untouched -> legacy random rule (unchanged behaviour)
 *   "uniform"  every option equally likely
 *   "weighted" use this.weights
 * overrides: unit index -> weight list (always wins over mode)
 * Empty/zero weights are treated as inherit, so a half-filled config can
 * never dead-end the picker.
 */
export class AnswerConfig {
  readonly mode: ConfigMode;
  readonly weights: number[];
  readonly overrides: Map<number, number[]>;

  constructor(
    mode: ConfigMode = "default",
    weights?: unknown,
    overrides?: Record<string | number, unknown> | Map<number, unknown>,
  ) {
    this.mode = MODES.includes(mode) ? mode : "default";
    this.weights = cleanList(weights);

    const raw = new Map<number, unknown>();
    if (overrides instanceof Map) {
      for (const [idx, vals] of overrides) raw.set(Number(idx), vals);
    } else if (overrides) {
      for (const [idx, vals] of Object.entries(overrides)) raw.set(Number(idx), vals);
    }
    this.overrides = new Map(
      [...raw].map(([idx, vals]) => [idx, cleanList(vals)] as const),
    );
  }

  get isUntouched(): boolean {
    return this.mode === "default" && this.overrides.size === 0;
  }

  /** Resolve the weights for one unit. */
  resolve(idx: number, n: number): Resolved {
    const override = this.overrides.get(idx);
    if (override) {
      const fitted = fit(override, n);
      if (fitted) return { kind: "weighted", weights: fitted };
    }

    if (this.mode === "weighted") {
      const fitted = fit(this.weights, n);
      if (fitted) return { kind: "weighted", weights: fitted };
      return { kind: "uniform", weights: null };
    }

    if (this.mode === "uniform") return { kind: "uniform", weights: null };
    return { kind: "default", weights: null };
  }

  toJSON(): AnswerConfigData {
    return {
      mode: this.mode,
      weights: [...this.weights],
      overrides: Object.fromEntries(
        [...this.overrides].map(([idx, vals]) => [String(idx), [...vals]]),
      ),
    };
  }

  static fromJSON(data: AnswerConfigData | null | undefined): AnswerConfig {
    const d = data ?? ({} as AnswerConfigData);
    return new AnswerConfig(d.mode ?? "default", d.weights, d.overrides);
  }
}
