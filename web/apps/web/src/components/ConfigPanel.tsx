"use client";

import { useState } from "react";
import type { AnswerConfigData, ConfigMode } from "@/lib/core";
import { MODES } from "@/lib/core";

interface Props {
  config: AnswerConfigData;
  onChange: (next: AnswerConfigData) => void;
  referenceOptions: string[];
  unitCount: number;
  unitLabels: string[];
  disabled: boolean;
}

function parseWeights(raw: string): number[] {
  return raw
    .split(/[\s,]+/)
    .filter((s) => s.length > 0)
    .map((s) => Number(s))
    .filter((n) => Number.isFinite(n) && n >= 0);
}

function WeightsInput({
  value,
  onCommit,
  labels,
  disabled,
  placeholder = "1, 3, 5",
}: {
  value: number[];
  onCommit: (next: number[]) => void;
  labels: string[];
  disabled: boolean;
  placeholder?: string;
}) {
  const [raw, setRaw] = useState(() => value.join(", "));

  return (
    <div className="flex flex-col gap-1.5">
      <input
        className="input-glass label-mono w-full rounded-lg px-2.5 py-1.5 text-[12px]"
        value={raw}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => setRaw(e.target.value)}
        onBlur={() => onCommit(parseWeights(raw))}
        onKeyDown={(e) => {
          if (e.key === "Enter") onCommit(parseWeights(raw));
        }}
      />
      {labels.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {labels.map((label, i) => (
            <span
              key={`${label}-${i}`}
              className="rounded bg-input/70 px-1.5 py-0.5 text-[10px] text-muted"
            >
              {label || `opt ${i + 1}`}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ConfigPanel({
  config,
  onChange,
  referenceOptions,
  unitCount,
  unitLabels,
  disabled,
}: Props) {
  const [openUnits, setOpenUnits] = useState<Set<number>>(new Set());

  const setMode = (mode: ConfigMode) => onChange({ ...config, mode });

  const setWeights = (weights: number[]) => onChange({ ...config, weights });

  const setOverride = (idx: number, weights: number[]) => {
    const overrides = { ...config.overrides };
    if (weights.length === 0) delete overrides[String(idx)];
    else overrides[String(idx)] = weights;
    onChange({ ...config, overrides });
  };

  const hasOverride = (idx: number) =>
    Object.prototype.hasOwnProperty.call(config.overrides, String(idx));

  const toggleUnit = (idx: number) => {
    setOpenUnits((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <div className="flex flex-col gap-5">
      <section>
        <h3 className="label-mono mb-2 text-[10px] tracking-[0.24em] text-muted">
          GLOBAL MODE
        </h3>
        <div className="grid grid-cols-3 gap-1.5">
          {MODES.map((mode) => (
            <button
              key={mode}
              type="button"
              data-active={config.mode === mode}
              disabled={disabled}
              onClick={() => setMode(mode)}
              className="btn-ghost label-mono rounded-lg px-2 py-2 text-[10px] tracking-[0.12em] uppercase disabled:opacity-40"
            >
              {mode}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] leading-snug text-muted">
          {config.mode === "default" &&
            "Legacy behaviour: untouched random rule, exactly like the desktop app."}
          {config.mode === "uniform" && "Every option equally likely."}
          {config.mode === "weighted" && "Use the global weight list below."}
        </p>
      </section>

      {config.mode === "weighted" && (
        <section className="anim-up">
          <h3 className="label-mono mb-2 text-[10px] tracking-[0.24em] text-muted">
            GLOBAL WEIGHTS
          </h3>
          <WeightsInput
            key={`global-${config.weights.join(",")}`}
            value={config.weights}
            onCommit={setWeights}
            labels={referenceOptions}
            disabled={disabled}
          />
        </section>
      )}

      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h3 className="label-mono text-[10px] tracking-[0.24em] text-muted">
            PER-UNIT OVERRIDES
          </h3>
          <span className="label-mono text-[10px] text-muted">
            {Object.keys(config.overrides).length}/{unitCount}
          </span>
        </div>

        {unitCount === 0 ? (
          <p className="text-[11px] text-muted">
            No pickable units yet — analyze a form first.
          </p>
        ) : (
          <div className="flex max-h-[38vh] flex-col gap-1.5 overflow-y-auto pr-1">
            {unitLabels.map((label, idx) => {
              const on = hasOverride(idx);
              const open = openUnits.has(idx);
              return (
                <div key={idx} className="glass-soft rounded-lg p-2">
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => toggleUnit(idx)}
                    className="flex w-full items-center gap-2 text-left"
                  >
                    <span className="label-mono w-6 shrink-0 text-[10px] text-muted">
                      {String(idx).padStart(2, "0")}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-[12px] text-lavender">
                      {label}
                    </span>
                    <span
                      className="label-mono shrink-0 rounded px-1.5 py-0.5 text-[9px] tracking-[0.1em]"
                      style={{
                        color: on ? "#8FE9FF" : "#9C8FC4",
                        border: `1px solid ${on ? "rgba(143,233,255,0.5)" : "rgba(156,143,196,0.3)"}`,
                      }}
                    >
                      {on ? "OVERRIDE" : "INHERIT"}
                    </span>
                  </button>

                  {open && (
                    <div className="anim-up mt-2">
                      <WeightsInput
                        key={`${idx}-${(config.overrides[String(idx)] ?? []).join(",")}`}
                        value={config.overrides[String(idx)] ?? []}
                        onCommit={(w) => setOverride(idx, w)}
                        labels={[]}
                        disabled={disabled}
                        placeholder="blank = inherit, e.g. 3,1,1"
                      />
                      {on ? (
                        <button
                          type="button"
                          disabled={disabled}
                          onClick={() => setOverride(idx, [])}
                          className="btn-ghost label-mono mt-1.5 rounded px-2 py-1 text-[10px]"
                        >
                          CLEAR OVERRIDE
                        </button>
                      ) : (
                        <p className="label-mono mt-1.5 text-[10px] text-muted">
                          Enter weights to override this unit.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
