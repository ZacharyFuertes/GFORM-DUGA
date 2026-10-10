"use client";

import { useEffect, useRef } from "react";

interface Mote {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  hue: number;
}

/** Ambient drifting motes behind the glass panels. */
export default function AmbientBackdrop() {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const motes: Mote[] = [];
    let raf = 0;
    let w = 0;
    let h = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();

    const count = 46;
    for (let i = 0; i < count; i++) {
      motes.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.18,
        vy: -0.06 - Math.random() * 0.2,
        r: 0.6 + Math.random() * 2.1,
        hue: Math.random() < 0.72 ? 276 : 194,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      for (const m of motes) {
        if (!reduce) {
          m.x += m.vx;
          m.y += m.vy;
          if (m.y < -8) {
            m.y = h + 8;
            m.x = Math.random() * w;
          }
          if (m.x < -8) m.x = w + 8;
          if (m.x > w + 8) m.x = -8;
        }
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.r, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${m.hue}, 88%, 72%, 0.5)`;
        ctx.fill();
      }
      raf = window.requestAnimationFrame(draw);
    };

    draw();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      window.cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className="pointer-events-none fixed inset-0 h-full w-full opacity-70"
    />
  );
}
