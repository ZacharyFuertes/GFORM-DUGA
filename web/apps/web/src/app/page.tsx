"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnswerConfig, makePicker } from "@/lib/core";
import type { AnswerConfigData, FormSchema } from "@/lib/core";
import AmbientBackdrop from "@/components/AmbientBackdrop";
import ConfigPanel from "@/components/ConfigPanel";
import FormView from "@/components/FormView";
import LiveLog from "@/components/LiveLog";
import type { LogLine } from "@/components/LiveLog";
import StatusPill from "@/components/StatusPill";
import type { PillTone } from "@/components/StatusPill";
import { cancelRun, createRun, fetchRun, fetchRunEvents, subscribeRun } from "@/lib/runs";
import type { RunEventRow, RunRow } from "@/lib/runs";

type Status = "idle" | "analyzing" | "ready" | "error";

let LOG_SEQUENCE = 0;

const EMPTY_CONFIG: AnswerConfigData = {
  mode: "default",
  weights: [],
  overrides: {},
};

const TONE: Record<Status, PillTone> = {
  idle: "idle",
  analyzing: "busy",
  ready: "ok",
  error: "bad",
};

export default function Home() {
  const [url, setUrl] = useState("");
  const [count, setCount] = useState(3);
  const [status, setStatus] = useState<Status>("idle");
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [config, setConfig] = useState<AnswerConfigData>(EMPTY_CONFIG);
  const [preview, setPreview] = useState<Record<number, number> | null>(null);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [activeRun, setActiveRun] = useState<RunRow | null>(null);

  const lastSeqRef = useRef(0);
  const unsubRef = useRef<(() => void) | null>(null);

  const push = useMemo(() => {
    return (text: string, tone: LogLine["tone"] = "info") =>
      setLines((prev) => {
        LOG_SEQUENCE += 1;
        const added: LogLine[] = [{ id: LOG_SEQUENCE, text, tone }];
        return [...prev, ...added].slice(-400);
      });
  }, []);

  const pushEvent = useCallback(
    (e: RunEventRow) => {
      if (e.seq <= lastSeqRef.current) return;
      lastSeqRef.current = e.seq;
      const tone: LogLine["tone"] = e.level === "ok" ? "ok" : e.level === "err" ? "err" : e.level === "warn" ? "warn" : "info";
      push(e.message, tone);
    },
    [push],
  );

  // Cleanup subscription on unmount / next run.
  useEffect(() => {
    return () => {
      unsubRef.current?.();
      unsubRef.current = null;
    };
  }, []);

  const runIsActive =
    activeRun !== null && (activeRun.status === "queued" || activeRun.status === "running");
  const busy = status === "analyzing" || runIsActive;

  const unitLabels = useMemo(
    () => (schema ? schema.units.map((u) => u.label) : []),
    [schema],
  );

  async function handleAnalyze() {
    if (busy) return;
    setStatus("analyzing");
    setSchema(null);
    setPreview(null);
    push(`analyzing ${url.trim() || "(no url)"} ...`, "info");

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const body = (await res.json()) as FormSchema | { error: string };

      if (body && typeof body === "object" && "error" in body) {
        setStatus("error");
        push(body.error || "Analyze failed.", "err");
        return;
      }

      const data = body as FormSchema;
      setSchema(data);
      setConfig(EMPTY_CONFIG);
      setStatus("ready");
      push(`form: ${data.title}`, "ok");
      push(`${data.questions.length} questions / ${data.units.length} units`, "ok");
    } catch (exc) {
      setStatus("error");
      push(String(exc), "err");
    }
  }

  function handleSample() {
    if (!schema) return;
    const answerConfig = AnswerConfig.fromJSON(config);
    const pick = makePicker(answerConfig);
    const out: Record<number, number> = {};
    const picked: string[] = [];

    for (const u of schema.units) {
      const idx = pick(u.index, u.options.length);
      out[u.index] = idx;
      if (picked.length < 6) {
        picked.push(`#${u.index} ${u.label} -> ${u.options[idx] ?? "?"}`);
      }
    }

    setPreview(out);
    push(
      config.mode === "default" && Object.keys(config.overrides).length === 0
        ? "sample draw (legacy default rule)"
        : `sample draw (mode: ${config.mode})`,
      "ok",
    );
    for (const line of picked) push(line, "info");
    if (schema.units.length > 6) {
      push(`... ${schema.units.length - 6} more units`, "info");
    }
  }

  function subscribeToRun(runId: number) {
    if (unsubRef.current) {
      unsubRef.current();
      unsubRef.current = null;
    }
    lastSeqRef.current = 0;

    void fetchRun(runId).then((run) => {
      if (run) setActiveRun(run);
    });
    void fetchRunEvents(runId).then((events) => {
      for (const e of events) pushEvent(e);
    });

    unsubRef.current = subscribeRun(
      runId,
      (e) => pushEvent(e),
      (r) => {
        setActiveRun((prev) => (prev ? { ...prev, ...r } : r));
        if (r.status === "done") {
          push("run complete", "ok");
          setStatus("ready");
        } else if (r.status === "failed") {
          push(r.error || "run failed", "err");
          setStatus("error");
        } else if (r.status === "cancelled") {
          push("run cancelled", "warn");
          setStatus("ready");
        }
      },
    );
  }

  async function handleRun() {
    if (!schema || runIsActive) return;
    try {
      const run = await createRun(url.trim() || schema.title, schema, config, count);
      setActiveRun(run);
      push(
        `run #${run.id} queued (${count} submissions, mode: ${config.mode})`,
        "info",
      );
      subscribeToRun(run.id);
    } catch (exc) {
      setStatus("error");
      push(exc instanceof Error ? exc.message : String(exc), "err");
    }
  }

  async function handleStop() {
    const run = activeRun;
    if (!run || !runIsActive) return;
    try {
      await cancelRun(run.id);
      push(`cancelling run #${run.id}...`, "warn");
    } catch (exc) {
      push(exc instanceof Error ? exc.message : String(exc), "err");
    }
  }

  const pillTone: PillTone = runIsActive ? "busy" : TONE[status];

  return (
    <>
      <AmbientBackdrop />

      <div className="relative z-10 flex h-dvh flex-col">
        <header className="glass mx-4 mt-4 flex items-center gap-4 rounded-2xl px-4 py-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="" className="h-9 w-9 rounded-lg" />
          <div className="min-w-0">
            <h1 className="label-mono text-[15px] tracking-[0.2em] text-lavender">
              GFORM-DUGA
            </h1>
            <p className="text-[11px] text-muted">
              analyze · randomize · submit
            </p>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <StatusPill tone={pillTone} />
          </div>
        </header>

        <div className="flex min-h-0 flex-1 gap-4 p-4">
          <aside className="glass hidden w-[320px] shrink-0 flex-col overflow-y-auto rounded-2xl p-4 lg:flex">
            <h2 className="label-mono mb-4 text-[11px] tracking-[0.24em] text-soft">
              ANSWER CONFIG
            </h2>
            <ConfigPanel
              config={config}
              onChange={setConfig}
              referenceOptions={schema?.reference_options ?? []}
              unitCount={schema?.units.length ?? 0}
              unitLabels={unitLabels}
              disabled={!schema || runIsActive}
            />
          </aside>

          <main className="flex min-w-0 flex-1 flex-col gap-4">
            <div className="glass flex flex-wrap items-center gap-3 rounded-2xl p-4">
              <input
                className="input-glass label-mono min-w-[200px] flex-1 rounded-xl px-3.5 py-2.5 text-[13px]"
                placeholder="https://docs.google.com/forms/d/..."
                value={url}
                disabled={busy}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleAnalyze();
                }}
              />
              <button
                type="button"
                className="btn-neon label-mono rounded-xl px-5 py-2.5 text-[12px] tracking-[0.16em]"
                disabled={busy}
                onClick={() => void handleAnalyze()}
              >
                {status === "analyzing" ? "ANALYZING..." : "ANALYZE"}
              </button>
              <button
                type="button"
                className="btn-ghost label-mono rounded-xl px-4 py-2.5 text-[12px] tracking-[0.16em] disabled:opacity-40"
                disabled={!schema || runIsActive}
                onClick={handleSample}
              >
                SAMPLE DRAW
              </button>
              <button
                type="button"
                className="btn-ghost label-mono rounded-xl px-4 py-2.5 text-[12px] tracking-[0.16em] disabled:opacity-40"
                disabled={lines.length === 0}
                onClick={() => setLines([])}
              >
                CLEAR LOG
              </button>

              <div className="ml-auto flex items-center gap-2 border-l border-line pl-3">
                <span className="label-mono text-[10px] tracking-[0.14em] text-muted">
                  RUN&nbsp;×
                </span>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={count}
                  disabled={runIsActive}
                  onChange={(e) =>
                    setCount(Math.max(1, Math.min(100, Number(e.target.value) || 1)))
                  }
                  className="input-glass label-mono w-16 rounded-lg px-2 py-2 text-center text-[13px]"
                />
                <button
                  type="button"
                  className="btn-neon label-mono rounded-xl px-4 py-2.5 text-[12px] tracking-[0.16em]"
                  disabled={!schema || runIsActive}
                  onClick={() => void handleRun()}
                >
                  {runIsActive
                    ? `RUNNING ${activeRun!.progress}/${activeRun!.count}`
                    : "RUN"}
                </button>
                <button
                  type="button"
                  className="btn-ghost label-mono rounded-xl px-3 py-2.5 text-[12px] tracking-[0.16em] disabled:opacity-40"
                  disabled={!runIsActive}
                  onClick={() => void handleStop()}
                >
                  STOP
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              {schema ? (
                <FormView schema={schema} preview={preview} />
              ) : (
                <div className="glass flex h-full min-h-[320px] flex-col items-center justify-center gap-3 rounded-2xl px-6 text-center">
                  <p className="label-mono text-[12px] tracking-[0.24em] text-soft">
                    NO FORM LOADED
                  </p>
                  <p className="max-w-md text-[13px] leading-relaxed text-muted">
                    Paste a Google Form link above and hit ANALYZE. The form is
                    parsed server-side, then you tune the randomness before any
                    submission happens.
                  </p>
                </div>
              )}
            </div>
          </main>

          <aside className="hidden w-[360px] shrink-0 flex-col md:flex">
            <LiveLog lines={lines} />
          </aside>
        </div>
      </div>
    </>
  );
}