"use client";

import type { AnswerConfigData, FormSchema } from "@gform/core";
import { ensureSession, getSupabase } from "./supabase";

export type RunStatus = "queued" | "running" | "done" | "failed" | "cancelled";
export type RunEventLevel = "info" | "ok" | "warn" | "err";

export interface RunRow {
  id: number;
  status: RunStatus;
  progress: number;
  count: number;
  created_at: string;
  error?: string | null;
}

export interface RunEventRow {
  seq: number;
  level: RunEventLevel;
  message: string;
  data?: unknown;
}

/** Upsert the analyzed form for this user, then enqueue a run. */
export async function createRun(
  url: string,
  schema: FormSchema,
  config: AnswerConfigData,
  count: number,
): Promise<RunRow> {
  const sb = getSupabase();
  if (!sb) throw new Error("Supabase is not configured.");

  const authed = await ensureSession();
  if (!authed) throw new Error("Could not sign in anonymously. Check Supabase anonymous sign-in is enabled.");

  const { data: form, error: formError } = await sb
    .from("forms")
    .upsert(
      {
        url,
        title: schema.title,
        description: schema.description,
        schema,
      },
      { onConflict: "user_id,url" },
    )
    .select("id")
    .single();
  if (formError) throw formError;

  const { data: run, error: runError } = await sb
    .from("runs")
    .insert({ form_id: form.id, url, config, count })
    .select("id, status, progress, count, created_at")
    .single();
  if (runError) throw runError;
  return run as RunRow;
}

export async function fetchRun(runId: number): Promise<RunRow | null> {
  const sb = getSupabase();
  if (!sb) return null;
  const { data } = await sb.from("runs").select("id, status, progress, count, created_at, error").eq("id", runId).single();
  return data ? (data as RunRow) : null;
}

export async function fetchRunEvents(runId: number, afterSeq = 0): Promise<RunEventRow[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const { data } = await sb
    .from("run_events")
    .select("seq, level, message, data")
    .eq("run_id", runId)
    .gt("seq", afterSeq)
    .order("seq", { ascending: true });
  return (data ?? []) as RunEventRow[];
}

export async function cancelRun(runId: number): Promise<void> {
  const sb = getSupabase();
  if (!sb) return;
  await sb.from("runs").update({ status: "cancelled" }).eq("id", runId);
}

/** Subscribe to live run_events and runs changes. Returns an unsubscribe fn. */
export function subscribeRun(
  runId: number,
  onEvent: (e: RunEventRow) => void,
  onRun: (r: RunRow) => void,
): () => void {
  const sb = getSupabase();
  if (!sb) return () => {};

  const channel = sb
    .channel(`run-${runId}`)
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "run_events", filter: `run_id=eq.${runId}` },
      (payload) => {
        const row = payload.new as { seq: number; level: string; message: string; data?: unknown };
        onEvent({ seq: row.seq, level: row.level as RunEventLevel, message: row.message, data: row.data });
      },
    )
    .on(
      "postgres_changes",
      { event: "UPDATE", schema: "public", table: "runs", filter: `id=eq.${runId}` },
      (payload) => {
        const r = payload.new as RunRow;
        if (typeof r === "object" && r !== null) onRun(r);
      },
    )
    .subscribe();

  return () => {
    void sb.removeChannel(channel);
  };
}