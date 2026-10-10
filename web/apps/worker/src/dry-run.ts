import { AnswerConfig, makePicker } from "@gform/core";
import { chromium } from "playwright-core";
import { buildNamePool } from "./people.ts";
import { submitForm } from "./smart-fill.ts";

/**
 * Local smoke runner: submits to a real Google Form N times with a config,
 * printing results. No Supabase involved.
 *
 *   node src/dry-run.ts --url https://... --count 3 [--config answer-config.json]
 */
const args: Record<string, string> = {};
for (let i = 2; i < process.argv.length; i++) {
  const arg = process.argv[i] as string;
  if (arg.startsWith("--")) {
    args[arg.slice(2)] = process.argv[i + 1] ?? "true";
    i += 1;
  }
}

const url = args.url;
if (!url) {
  console.error("usage: node src/dry-run.ts --url <form> [--count N] [--config file.json]");
  process.exit(1);
}
const count = Number(args.count ?? "1");
let config: AnswerConfig = new AnswerConfig();
if (args.config) {
  try {
    const raw = await import("node:fs").then((fs) => fs.readFileSync(args.config as string, "utf8"));
    config = AnswerConfig.fromJSON(JSON.parse(raw));
  } catch (exc) {
    console.warn(`could not read config ${args.config}; using defaults (${exc})`);
  }
}

const pick = makePicker(config);
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  userAgent:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" +
    " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
});

let namePool = buildNamePool();
let ok = 0;
let fail = 0;

for (let i = 1; i <= count; i++) {
  if (namePool.length === 0) namePool = buildNamePool();
  const outcome = await submitForm(context, i, count, namePool, url, pick, (m) => console.error(m));
  if (outcome.ok) ok += 1;
  else fail += 1;
  const label = outcome.data.name ?? outcome.data.reason ?? "?";
  const summary = outcome.data.answers.map(([, v]) => v).join(", ") || "no answers";
  console.log(`[${i}/${count}] ${outcome.ok ? "OK  " : "FAIL"} ${label} -> ${summary}`);
  if (i < count) await new Promise((r) => setTimeout(r, 1000 + Math.floor(Math.random() * 2000)));
}

await context.close();
await browser.close();
console.log(`done: ${ok} submitted, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);