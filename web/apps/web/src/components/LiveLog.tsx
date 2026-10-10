"use client";

import { useEffect, useRef, useState } from "react";

export interface LogLine {
  id: number;
  text: string;
  tone: "info" | "ok" | "warn" | "err";
}

const COLORS: Record<LogLine["tone"], string> = {
  info: "#C77DFF",
  ok: "#7CF7B0",
  warn: "#FFD166",
  err: "#FF7AB6",
};

export default function LiveLog({ lines }: { lines: LogLine[] }) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [follow, setFollow] = useState(true);

  useEffect(() => {
    if (!follow) return;
    const el = boxRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines, follow]);

  return (
    <section className="glass relative flex h-full min-h-0 flex-col overflow-hidden rounded-2xl">
      <header className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <h2 className="label-mono text-[11px] tracking-[0.22em] text-soft">
          LIVE LOG
        </h2>
        <button
          type="button"
          onClick={() => setFollow((v) => !v)}
          className="btn-ghost label-mono rounded-md px-2 py-0.5 text-[10px] tracking-[0.14em]"
          data-active={follow}
        >
          {follow ? "FOLLOW" : "PAUSED"}
        </button>
      </header>

      <div className="relative min-h-0 flex-1">
        <div
          aria-hidden
          className="anim-scan pointer-events-none absolute inset-x-0 top-0 h-16"
          style={{
            background:
              "linear-gradient(180deg, transparent, rgba(184,77,255,0.16), transparent)",
          }}
        />
        <div
          ref={boxRef}
          className="label-mono h-full overflow-y-auto px-4 py-3 text-[12px] leading-[1.65]"
        >
          {lines.length === 0 ? (
            <p className="text-muted/70">
              &gt; awaiting operator input<span className="anim-pulse">_</span>
            </p>
          ) : (
            lines.map((l) => (
              <div key={l.id} className="anim-up break-words">
                <span className="text-muted/70">&gt;&nbsp;</span>
                <span style={{ color: COLORS[l.tone] }}>{l.text}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
