import type { AnalyzeError, AnalyzeResult, Question, Row, Unit } from "./types";

const TYPE_LABELS: Record<number, string> = {
  0: "Short Text",
  1: "Long Text",
  2: "Multiple Choice",
  3: "Dropdown",
  4: "Checkboxes",
  5: "Linear Scale",
  6: "Date",
  7: "Grid / Matrix",
  8: "Section Header",
  9: "Time",
};

/** Question types the bot picks through a div[role="radiogroup"]. */
const RADIO_TYPES = new Set([2, 5, 7]);

const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

type Arr = unknown[];

function asArray(value: unknown): Arr | null {
  return Array.isArray(value) ? value : null;
}

function isAnalyzeError(result: AnalyzeResult): result is AnalyzeError {
  return typeof (result as AnalyzeError).error === "string";
}

export { isAnalyzeError };

/** One entry per answerable row: grid = N rows, plain choice = 1 row. */
function parseRows(question: Arr, typeCode: number): Row[] {
  const body = question.length > 4 ? asArray(question[4]) : null;
  if (!body || body.length === 0) return [];

  if (typeCode === 5) {
    // Linear scale stores [entry_id, [min, max], required].
    const row = asArray(body[0]);
    const scale = row ? asArray(row[1]) : null;
    if (!row || !scale) return [];
    const low = Number(scale[0]);
    const high = Number(scale[1]);
    if (!Number.isFinite(low) || !Number.isFinite(high) || high < low) return [];
    const options: string[] = [];
    for (let v = low; v <= high; v++) options.push(String(v));
    return [{ entry_id: row[0] ?? null, label: "", options }];
  }

  const rows: Row[] = [];
  for (const raw of body) {
    const row = asArray(raw);
    if (!row || row.length === 0) continue;
    const rowEntryId = row[0] ?? null;

    const options: string[] = [];
    const rowOptions = asArray(row[1]);
    if (rowOptions) {
      for (const option of rowOptions) {
        const nested = asArray(option);
        if (nested) {
          options.push(nested[0] == null ? "" : String(nested[0]));
        } else {
          options.push(String(option));
        }
      }
    }

    const labelSlot = asArray(row[3]);
    const rowLabel = labelSlot && labelSlot.length > 0
      ? String(labelSlot[0] ?? "")
      : "";

    rows.push({ entry_id: rowEntryId, label: rowLabel, options });
  }
  return rows;
}

/** The most common option list, used to label the global weights row. */
function referenceOptions(units: Unit[]): string[] {
  const same = (a: string[], b: string[]) =>
    a.length === b.length && a.every((v, i) => v === b[i]);

  let best: string[] = [];
  let bestCount = 0;
  for (const unit of units) {
    const count = units.reduce(
      (n, other) => n + (same(other.options, unit.options) ? 1 : 0),
      0,
    );
    if (count > bestCount) {
      best = unit.options;
      bestCount = count;
    }
  }
  return best;
}

/**
 * Flatten a fetched Google Form page into displayable questions and units.
 * Pure and synchronous — used by analyze() and by the offline tests.
 */
export function parseFormHtml(html: string): AnalyzeResult {
  const match = /var FB_PUBLIC_LOAD_DATA_ = ([\s\S]*?);<\/script>/.exec(html);
  if (!match) {
    return {
      error: "Could not find form data. Is this a valid Google Form link?",
    };
  }

  let data: unknown;
  try {
    data = JSON.parse(match[1] as string);
  } catch (exc) {
    return { error: `Could not parse form data: ${exc}` };
  }

  const root = asArray(data);
  if (!root || root.length < 2 || root[1] == null) {
    return { error: "Form data structure is invalid." };
  }

  const meta = asArray(root[1]);
  if (!meta) return { error: "Form data structure is invalid." };

  const title =
    meta.length > 8 && meta[8] != null ? String(meta[8]) : "Untitled Form";
  const description = typeof meta[0] === "string" ? meta[0] : "";
  const questionList = asArray(meta.length > 1 ? meta[1] : []) ?? [];

  const questions: Question[] = [];
  const units: Unit[] = [];

  for (const entry of questionList) {
    const q = asArray(entry);
    if (!q || q.length < 4) continue;

    const label = (q[1] as string) || "";
    const typeCode = Number(q[3]);

    let rawEntryId: unknown = null;
    let required = false;
    const body = asArray(q[4]);
    const first = body && body.length > 0 ? asArray(body[0]) : null;
    if (first) {
      rawEntryId = first[0] ?? null;
      if (first.length > 2) required = Boolean(first[2]);
    }

    const rows = parseRows(q, typeCode);

    questions.push({
      label,
      type: TYPE_LABELS[typeCode] ?? `Unknown (${typeCode})`,
      type_code: typeCode,
      entry_id:
        rawEntryId != null ? `entry.${rawEntryId}` : "No ID (Header/Info)",
      required,
      rows,
    });

    if (RADIO_TYPES.has(typeCode)) {
      for (const row of rows) {
        units.push({
          index: units.length,
          question: label,
          label: row.label || label,
          options: row.options,
          entry_id: row.entry_id,
          required,
        });
      }
    }
  }

  return {
    title,
    description,
    questions,
    units,
    reference_options: referenceOptions(units),
  };
}

/** Fetch a Google Form URL and parse it. Server-side only (no CORS). */
export async function analyze(
  url: string,
  init: { timeoutMs?: number } = {},
): Promise<AnalyzeResult> {
  let response: Response;
  try {
    response = await fetch(url, {
      headers: {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
      },
      signal: AbortSignal.timeout(init.timeoutMs ?? 15_000),
    });
  } catch (exc) {
    return { error: String(exc) };
  }

  if (!response.ok) {
    return {
      error: `Failed to fetch form. Status: ${response.status}`,
    };
  }

  return parseFormHtml(await response.text());
}