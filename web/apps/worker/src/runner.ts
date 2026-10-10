import { AnswerConfig, makePicker } from "@gform/core";
import type { SupabaseClient } from "@supabase/supabase-js";
import { chromium } from "playwright-core";
import { buildNamePool } from "./people.ts";
import type { Name } from "./people.ts";
import { submitForm } from "./smart-fill.ts";
import type { EventLevel } from "./smart-fill.ts";

export interface RunRow {
  id: number;
  status: string;
  progress: number;
  count: number;
  url: string;
  config: unknown;
  form_id: number;
}

interface Event {
  seq: number;
  level: EventLevel;
  message: string;
  data?: unknown;
}

/** Batches run_events flushes so the free tier does not hit its insert limits. */
class EventSink {
  private seq = 0;
  private buffer: Array<Omit<Event, "seq">> = [];
  private readonly supabase: SupabaseClient;
  private readonly runId: number;

  constructor(supabase: SupabaseClient, runId: number) {
    // No parameter properties: Node runs this file via native type-stripping,
    // which does not transform constructor parameter properties.
    this.supabase = supabase;
    this.runId = runId;
  }

  emit(level: EventLevel, message: string, data?: unknown): void {
    this.seq += 1;
    this.buffer.push({ level, message, data });
  }

  async flush(): Promise<void> {
    if (this.buffer.length === 0) return;
    const rows = this.buffer.map((e, i) => ({
      run_id: this.runId,
      seq: this.seq - this.buffer.length + i + 1,
      ...e,
    }));
    this.buffer = [];
    const { error } = await this.supabase.from("run_events").insert(rows);
    if (error) {
      console.error(`run ${this.runId}: could not persist events:`, error.message);
    }
  }
}

function summarize(answers: Array<[string, string]>): string {
  if (answers.length === 0) return "no answers";
  return answers.map(([, v]) => v).join(", ");
}

async function isCancelled(supabase: SupabaseClient, runId: number): Promise<boolean> {
  const { data } = await supabase
    .from("runs")
    .select("status")
    .eq("id", runId)
    .single();
  return data?.status === "cancelled";
}

/**
 * Execute one claimed run: load the stored schema + config, then submit
 * `count` times with the same browser context.
 */
export async function executeRun(
  supabase: SupabaseClient,
  run: RunRow,
  leaseSeconds: number,
): Promise<void> {
  const sink = new EventSink(supabase, run.id);
  const { data: form, error: formError } = await supabase
    .from("forms")
    .select("schema, title")
    .eq("id", run.form_id)
    .single();

  if (formError || !form) {
    await supabase.from("runs").update({ status: "failed", error: formError?.message ?? "form not found" }).eq("id", run.id);
    return;
  }

  const schema = form.schema as { units: Array<{ options: string[] }> };
  const answerConfig = AnswerConfig.fromJSON(run.config as never);
  const pick = makePicker(answerConfig);
  const mode = answerConfig.isUntouched ? "default" : answerConfig.mode;

  sink.emit("info", `[run ${run.id}] form: ${form.title}`);
  sink.emit("info", `[run ${run.id}] ${run.count} submissions, randomness: ${mode}, overrides: ${answerConfig.overrides.size}`);
  await sink.flush();

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (exc) {
    const message = exc instanceof Error ? exc.message : String(exc);
    await supabase.from("runs").update({ status: "failed", error: `browser launch failed: ${message}` }).eq("id", run.id);
    sink.emit("err", `[run ${run.id}] browser launch failed: ${message}`);
    await sink.flush();
    return;
  }

  const context = await browser.newContext({
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" +
      " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  });
  let namePool = buildNamePool();

  let heartbeat: ReturnType<typeof setInterval> | null = null;
  if (leaseSeconds > 30) {
    heartbeat = setInterval(() => {
      void supabase.rpc("heartbeat_run", { target: run.id, lease_seconds: leaseSeconds });
    }, Math.min(15_000, Math.floor(leaseSeconds * 1000 * 0.5)));
  }

  let success = 0;
  let failed = 0;
  const names: string[] = [];

  try {
    for (let i = 1; i <= run.count; i++) {
      if (await isCancelled(supabase, run.id)) {
        sink.emit("warn", `[run ${run.id}] cancelled by user; stopping.`);
        await sink.flush();
        break;
      }

      if (namePool.length === 0) namePool = buildNamePool();

      const outcome = await submitForm(
        context,
        i,
        run.count,
        namePool,
        run.url,
        pick,
        (message) => sink.emit("err", message),
      );

      if (outcome.ok) success += 1;
      else failed += 1;
      if (outcome.data.name) names.push(outcome.data.name);

      const label = outcome.data.name ?? outcome.data.reason ?? "?";
      const summary = summarize(outcome.data.answers);
      sink.emit(
        outcome.ok ? "ok" : "err",
        `[${i}/${run.count}] ${outcome.ok ? "OK " : "FAIL"} ${label} -> ${summary}`,
        { ok: outcome.ok, name: outcome.data.name, answers: outcome.data.answers },
      );

      await supabase
        .from("runs")
        .update({ progress: i })
        .eq("id", run.id);
      await sink.flush();

      const delay = 1000 + Math.floor(Math.random() * 2000);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }

    const cancelled = await isCancelled(supabase, run.id);
    if (cancelled) {
      await supabase.from("runs").update({ status: "cancelled" }).eq("id", run.id);
      return;
    }

    sink.emit("info", `[run ${run.id}] SUMMARY: ${success} submitted, ${failed} failed, ${new Set(names).size} unique names`);
    await sink.flush();

    if (failed === 0) {
      await supabase.from("runs").update({ status: "done", progress: run.count }).eq("id", run.id);
    } else if (success === 0) {
      await supabase.from("runs").update({ status: "failed", progress: run.count }).eq("id", run.id);
    } else {
      await supabase.from("runs").update({ status: "done", progress: run.count }).eq("id", run.id);
    }
  } finally {
    if (heartbeat) clearInterval(heartbeat);
    await context.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}