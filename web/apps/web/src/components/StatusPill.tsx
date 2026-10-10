export type PillTone = "idle" | "busy" | "ok" | "bad";

const TONES: Record<PillTone, { dot: string; text: string; ring: string }> = {
  idle: { dot: "#9C8FC4", text: "IDLE", ring: "rgba(156,143,196,0.45)" },
  busy: { dot: "#8FE9FF", text: "BUSY", ring: "rgba(143,233,255,0.5)" },
  ok: { dot: "#7CF7B0", text: "READY", ring: "rgba(124,247,176,0.5)" },
  bad: { dot: "#FF7AB6", text: "ERROR", ring: "rgba(255,122,182,0.55)" },
};

export default function StatusPill({ tone }: { tone: PillTone }) {
  const t = TONES[tone];
  return (
    <span
      className="label-mono inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] tracking-[0.18em]"
      style={{
        color: t.text,
        border: `1px solid ${t.ring}`,
        background: "rgba(11,6,20,0.6)",
      }}
    >
      <span
        className={tone === "busy" ? "anim-pulse" : ""}
        style={{
          width: 7,
          height: 7,
          borderRadius: 99,
          background: t.dot,
          boxShadow: `0 0 9px ${t.dot}`,
        }}
      />
      {t.text}
    </span>
  );
}
