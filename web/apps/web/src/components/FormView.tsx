"use client";

import type { FormSchema } from "@/lib/core";

interface Props {
  schema: FormSchema;
  preview: Record<number, number> | null;
}

function typeColor(code: number): string {
  if (code === 7) return "#8FE9FF";
  if (code === 2 || code === 3 || code === 4) return "#C77DFF";
  if (code === 5) return "#FF7AB6";
  return "#9C8FC4";
}

export default function FormView({ schema, preview }: Props) {
  return (
    <div className="flex flex-col gap-5">
      <section className="glass rounded-2xl p-4">
        <p className="label-mono text-[10px] tracking-[0.24em] text-muted">FORM</p>
        <h2 className="mt-1 text-xl font-semibold text-lavender">{schema.title}</h2>
        {schema.description && (
          <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
            {schema.description}
          </p>
        )}
        <div className="label-mono mt-3 flex flex-wrap gap-3 text-[11px] text-muted">
          <span>{schema.questions.length} questions</span>
          <span>{schema.units.length} pickable units</span>
          <span>{schema.reference_options.length} reference options</span>
        </div>
      </section>

      <section>
        <h3 className="label-mono mb-2 text-[10px] tracking-[0.24em] text-muted">
          QUESTIONS
        </h3>
        <div className="flex flex-col gap-2">
          {schema.questions.length === 0 && (
            <p className="text-[12px] text-muted">No questions found.</p>
          )}
          {schema.questions.map((q, i) => (
            <article
              key={`${q.entry_id}-${i}`}
              className="glass-soft flex items-start gap-3 rounded-xl px-3 py-2.5"
            >
              <span className="label-mono mt-0.5 w-6 shrink-0 text-[11px] text-muted">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] leading-snug text-lavender">
                  {q.label || <span className="text-muted">(no label)</span>}
                </p>
                <p className="label-mono mt-1 truncate text-[10px] text-muted/80">
                  {q.entry_id}
                </p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                <span
                  className="label-mono rounded px-1.5 py-0.5 text-[9px] tracking-[0.1em]"
                  style={{
                    color: typeColor(q.type_code),
                    border: `1px solid ${typeColor(q.type_code)}55`,
                  }}
                >
                  {q.type.toUpperCase()}
                </span>
                {q.required && (
                  <span className="label-mono text-[9px] tracking-[0.1em] text-magenta">
                    REQUIRED
                  </span>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h3 className="label-mono mb-2 text-[10px] tracking-[0.24em] text-muted">
          PICKABLE UNITS
        </h3>
        <div className="flex flex-col gap-2">
          {schema.units.length === 0 && (
            <p className="text-[12px] text-muted">
              This form has no multiple-choice / scale / grid units.
            </p>
          )}
          {schema.units.map((u) => {
            const picked = preview ? preview[u.index] : undefined;
            return (
              <article
                key={u.index}
                className="glass-soft rounded-xl px-3 py-2.5"
              >
                <div className="flex items-baseline gap-3">
                  <span className="label-mono shrink-0 text-[11px] text-muted">
                    #{String(u.index).padStart(2, "0")}
                  </span>
                  <p className="min-w-0 flex-1 truncate text-[13px] text-lavender">
                    {u.label}
                  </p>
                  <span className="label-mono shrink-0 text-[10px] text-muted">
                    {u.options.length} opts
                  </span>
                </div>

                <div className="mt-2 flex flex-wrap gap-1.5">
                  {u.options.map((opt, i) => {
                    const chosen = picked === i;
                    return (
                      <span
                        key={`${opt}-${i}`}
                        className="label-mono rounded-md px-2 py-1 text-[11px] transition-colors"
                        style={{
                          background: chosen ? "rgba(184,77,255,0.32)" : "rgba(36,17,64,0.75)",
                          border: `1px solid ${chosen ? "#B84DFF" : "rgba(184,77,255,0.18)"}`,
                          color: chosen ? "#FFFFFF" : "#9C8FC4",
                          boxShadow: chosen ? "0 0 14px rgba(184,77,255,0.5)" : "none",
                        }}
                      >
                        {opt || `opt ${i + 1}`}
                      </span>
                    );
                  })}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
