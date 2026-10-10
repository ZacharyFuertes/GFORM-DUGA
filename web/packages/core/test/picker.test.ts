import assert from "node:assert/strict";
import { test } from "node:test";

import { AnswerConfig, defaultPick, fit } from "../src/answer-config.ts";
import { makePicker } from "../src/make-picker.ts";

function counts(pick: (i: number, n: number) => number, units: number, n: number, per: number) {
  const h = new Map<number, number>();
  for (let i = 0; i < units; i++) {
    for (let k = 0; k < per; k++) {
      const v = pick(i, n);
      h.set(v, (h.get(v) ?? 0) + 1);
    }
  }
  return h;
}

// ── legacy default rule ──────────────────────────────────────────────────────

test("untouched config never leaves the legacy 0..2 range on 5 options", () => {
  const pick = makePicker(new AnswerConfig());
  const seen = new Set<number>();
  for (let i = 0; i < 51; i++) {
    for (let k = 0; k < 100; k++) seen.add(pick(i, 5));
  }
  assert.deepEqual([...seen].sort((a, b) => a - b), [0, 1, 2]);
});

test("untouched config on 2 options only ever picks 0 or 1", () => {
  const pick = makePicker(new AnswerConfig());
  const seen = new Set<number>();
  for (let k = 0; k < 500; k++) seen.add(pick(0, 2));
  assert.deepEqual([...seen].sort((a, b) => a - b), [0, 1]);
});

test("untouched config on 7 options covers the whole range", () => {
  const pick = makePicker(new AnswerConfig());
  const seen = new Set<number>();
  for (let k = 0; k < 2000; k++) seen.add(k >= 0 ? pick(0, 7) : 0);
  assert.deepEqual([...seen].sort((a, b) => a - b), [0, 1, 2, 3, 4, 5, 6]);
});

test("defaultPick matches the desktop rules exactly", () => {
  for (let k = 0; k < 300; k++) {
    assert.ok(defaultPick(5) <= 2, "n==5 -> 0..2");
    assert.ok(defaultPick(2) <= 1, "n==2 -> 0..1");
    const wide = defaultPick(7);
    assert.ok(wide >= 0 && wide < 7, "n==7 -> 0..6");
  }
  assert.equal(defaultPick(0), 0);
});

// ── per-unit overrides ───────────────────────────────────────────────────────

test("override [100,0] on a 2-option unit always wins", () => {
  const pick = makePicker(new AnswerConfig("uniform", undefined, { 0: [100, 0] }));
  for (let k = 0; k < 500; k++) assert.equal(pick(0, 2), 0);
});

test("other units still follow uniform mode", () => {
  const pick = makePicker(new AnswerConfig("uniform", undefined, { 0: [100, 0] }));
  const h = new Map<number, number>();
  for (let i = 1; i < 5000; i++) {
    const v = pick(i, 5);
    h.set(v, (h.get(v) ?? 0) + 1);
  }
  assert.deepEqual([...h.keys()].sort((a, b) => a - b), [0, 1, 2, 3, 4]);
});

test("override [0,0,0,0,100] on a 5-option unit always picks index 4", () => {
  const pick = makePicker(new AnswerConfig("default", undefined, { 7: [0, 0, 0, 0, 100] }));
  for (let k = 0; k < 500; k++) assert.equal(pick(7, 5), 4);
});

test("a radio pick maps to a one-hot weight list", () => {
  const pick = makePicker(
    new AnswerConfig("default", undefined, { 0: [0, 0, 100, 0, 0] }),
  );
  for (let k = 0; k < 500; k++) assert.equal(pick(0, 5), 2);
});

// ── global weighted curve ────────────────────────────────────────────────────

test("weighted [0,0,20,40,40] reproduces the reference distribution", () => {
  const pick = makePicker(new AnswerConfig("weighted", [0, 0, 20, 40, 40]));
  const h = counts(pick, 51, 5, 200);
  const total = [...h.values()].reduce((a, b) => a + b, 0);

  assert.equal(total, 51 * 200, "sampled every pick");
  assert.equal(h.get(0) ?? 0, 0, "label '5' zeroed out");
  assert.equal(h.get(1) ?? 0, 0, "label '4' zeroed out");

  const c2 = h.get(2) ?? 0;
  const c3 = h.get(3) ?? 0;
  const c4 = h.get(4) ?? 0;
  assert.ok(c3 > c2 && c4 > c2, "'2','1' favoured over '3'");

  const share = c4 / total;
  assert.ok(Math.abs(share - 0.4) < 0.03, `label '1' ~40% -> ${share.toFixed(3)}`);
});

// ── config plumbing ──────────────────────────────────────────────────────────

test("untouched means default mode with no overrides", () => {
  assert.ok(new AnswerConfig().isUntouched);
  assert.ok(new AnswerConfig("uniform").isUntouched === false);
  assert.ok(new AnswerConfig("default", undefined, { 3: [1, 1] }).isUntouched === false);
});

test("toJSON/fromJSON round-trips", () => {
  const cfg = new AnswerConfig("weighted", [0, 0, 20, 40, 40], { 0: [0, 100] });
  const back = AnswerConfig.fromJSON(JSON.parse(JSON.stringify(cfg.toJSON())));

  assert.equal(back.mode, "weighted");
  assert.deepEqual(back.weights, [0, 0, 20, 40, 40]);
  assert.deepEqual(back.overrides.get(0), [0, 100]);
  assert.deepEqual(back.toJSON(), cfg.toJSON());
});

test("resolve falls back to uniform when global weights are unusable", () => {
  const cfg = new AnswerConfig("weighted", [0, 0, 0]);
  assert.deepEqual(cfg.resolve(0, 3), { kind: "uniform", weights: null });
});

test("fit resamples and rejects all-zero weights", () => {
  assert.deepEqual(fit([10, 20], 2), [10, 20]);
  assert.deepEqual(fit([10, 20], 1), [10]);
  assert.equal(fit([0, 0, 0], 3), null);
  assert.equal(fit([], 3), null);
  // Matches Python's banker's rounding: index 0 is chosen twice.
  assert.deepEqual(fit([0, 10], 3), [0, 0, 10]);
  assert.deepEqual(fit([1, 2, 3, 4, 5], 7), [1, 2, 2, 3, 4, 4, 5]);
});

test("empty and junk weights behave like the Python port", () => {
  const cfg = new AnswerConfig("default", ["abc", -5, "9"], { 1: "nope" } as never);
  assert.deepEqual(cfg.weights, [0, 0, 9]);
  assert.deepEqual(cfg.overrides.get(1), []);
  assert.equal(cfg.mode, "default");
});

test("picker never throws on a broken config", () => {
  const pick = makePicker(new AnswerConfig("weighted", [0, 0, 0]));
  for (let i = 0; i < 50; i++) {
    const v = pick(i, 5);
    assert.ok(v >= 0 && v < 5);
  }
  assert.equal(pick(0, 0), 0);
});
