import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

import { parseFormHtml } from "../src/analyze.ts";
import { isAnalyzeError } from "../src/analyze.ts";
import type { FormSchema } from "../src/types.ts";

const fixture = new URL("./fixtures/test2.html", import.meta.url);

async function loadFixture(): Promise<FormSchema> {
  const html = await readFile(fixture, "utf8");
  const result = parseFormHtml(html);
  assert.ok(!isAnalyzeError(result), isAnalyzeError(result) ? result.error : "");
  return result as FormSchema;
}

test("parses the offline fixture without network", async () => {
  const schema = await loadFixture();
  for (const key of ["title", "description", "questions", "units", "reference_options"]) {
    assert.ok(key in schema, `missing key: ${key}`);
  }
});

test("produces 51 answerable units", async () => {
  const schema = await loadFixture();
  assert.equal(schema.units.length, 51);
});

test("first unit is Gender with two options", async () => {
  const schema = await loadFixture();
  assert.deepEqual(schema.units[0], {
    index: 0,
    question: "Gender:*",
    label: "Gender:*",
    options: ["Male", "Female"],
    entry_id: 2133561483,
    required: true,
  });
});

test("ten grids, each contributing five 5-point rows", async () => {
  const schema = await loadFixture();
  const grids = schema.questions.filter((q) => q.type_code === 7);
  assert.equal(grids.length, 10);

  for (const grid of grids) {
    assert.equal(grid.rows.length, 5, grid.label);
    for (const row of grid.rows) {
      assert.deepEqual(row.options, ["5", "4", "3", "2", "1"], row.label);
    }
  }
});

test("reference option order is the 5..1 rating scale", async () => {
  const schema = await loadFixture();
  assert.deepEqual(schema.reference_options, ["5", "4", "3", "2", "1"]);
});

test("question metadata keeps label, type and entry id", async () => {
  const schema = await loadFixture();
  const short = schema.questions[0];
  assert.equal(short?.type, "Short Text");
  const grid = schema.questions[3];
  assert.equal(grid?.type, "Grid / Matrix");
  assert.equal(grid?.required, true);

  for (const q of schema.questions) {
    assert.ok(q.label.length > 0, "question label present");
    assert.ok(
      q.entry_id.startsWith("entry.") || q.entry_id === "No ID (Header/Info)",
      `entry id shape: ${q.entry_id}`,
    );
    assert.equal(typeof q.required, "boolean");
  }
});

test("unit indices are dense and zero-based", async () => {
  const schema = await loadFixture();
  schema.units.forEach((unit, i) => assert.equal(unit.index, i));
});

test("missing payload reports an error instead of throwing", () => {
  const result = parseFormHtml("<html><body>nothing here</body></html>");
  assert.ok(isAnalyzeError(result));
  assert.match((result as { error: string }).error, /Could not find form data/);
});
