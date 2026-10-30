"use client";

import { motion, useInView, useReducedMotion } from "framer-motion";
import { useRef } from "react";

const ease = [0.22, 1, 0.36, 1] as const;

/** Two bars: India's 60+ population in 2022 and 2050. */
export function GrowthBars() {
  const ref = useRef<HTMLDivElement>(null);
  const on = useInView(ref, { once: true, margin: "-80px" });
  const still = useReducedMotion();
  const bars = [
    { year: "2022", value: 149, label: "149M" },
    { year: "2050", value: 347, label: "347M" },
  ];
  return (
    <div ref={ref} className="growth" role="img" aria-label="Indians aged 60 and over: 149 million in 2022, 347 million projected for 2050">
      {bars.map((b, i) => (
        <div key={b.year} className="growth-col">
          <span className="growth-label">{b.label}</span>
          <div className="growth-track">
            <motion.i
              className={i ? "hi" : ""}
              initial={{ height: still ? `${(b.value / 347) * 100}%` : 0 }}
              animate={on ? { height: `${(b.value / 347) * 100}%` } : undefined}
              transition={{ duration: 1.2, delay: 0.2 + i * 0.25, ease }}
            />
          </div>
          <span className="growth-year">{b.year}</span>
        </div>
      ))}
    </div>
  );
}

/** Three circles with two filled: “2 in 3”. */
export function TwoInThree() {
  const ref = useRef<HTMLDivElement>(null);
  const on = useInView(ref, { once: true, margin: "-80px" });
  return (
    <div ref={ref} className="dots3" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <motion.span key={i} className={i < 2 ? "dot-on" : ""} initial={{ scale: 0.6, opacity: 0.3 }} animate={on ? { scale: 1, opacity: 1 } : undefined} transition={{ delay: 0.2 + i * 0.15, type: "spring", stiffness: 260, damping: 16 }} />
      ))}
    </div>
  );
}

/** A ring filled to `percent`. */
export function Ring({ percent }: { percent: number }) {
  const ref = useRef<SVGSVGElement>(null);
  const on = useInView(ref, { once: true, margin: "-80px" });
  const still = useReducedMotion();
  const r = 42;
  const c = 2 * Math.PI * r;
  return (
    <svg ref={ref} className="ring-viz" viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r={r} className="ring-bg" />
      <motion.circle
        cx="50" cy="50" r={r} className="ring-fg"
        strokeDasharray={c}
        initial={{ strokeDashoffset: still ? c * (1 - percent / 100) : c }}
        animate={on ? { strokeDashoffset: c * (1 - percent / 100) } : undefined}
        transition={{ duration: 1.4, delay: 0.2, ease }}
      />
    </svg>
  );
}
