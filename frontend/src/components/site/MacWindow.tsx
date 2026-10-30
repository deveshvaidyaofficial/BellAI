"use client";

import { AnimatePresence, motion } from "framer-motion";
import { BellRing, CalendarDays, Check, Clock, House, Maximize2, Minus, Phone, Users, X } from "lucide-react";
import { useEffect, useState } from "react";

type Mode = "open" | "min" | "closed" | "full";

const ROWS = {
  attention: [{ title: "Evening walk", sub: "Maya · no answer after 3 tries", chip: "Missed", tone: "bad" }],
  upcoming: [
    { title: "Drink a glass of water", sub: "Maya · today, 3:30 pm", chip: "Scheduled", tone: "" },
    { title: "Eye check-up with Dr. Rao", sub: "Maya · tomorrow, 9:00 am", chip: "Scheduled", tone: "" },
  ],
  calls: [{ title: "Blood pressure tablet", sub: "“Done. Thank you, dear.”", chip: "Confirmed", tone: "ok" }],
};

/** A macOS-style app window showing the family dashboard. The traffic lights work. */
export function MacWindow() {
  const [mode, setMode] = useState<Mode>("open");

  useEffect(() => {
    if (mode !== "full") return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMode("open");
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [mode]);

  const win = (full: boolean) => (
    <motion.div
      key="win"
      layoutId="mac-window"
      className={`mac ${full ? "full" : ""}`}
      initial={{ opacity: 0, scale: 0.9, y: 40 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={mode === "min" ? { opacity: 0, scale: 0.15, y: 260 } : { opacity: 0, scale: 0.92 }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
    >
      <div className="mac-bar">
        <div className="lights">
          <button type="button" className="tl red" aria-label="Close window" onClick={() => setMode("closed")}><X size={8} strokeWidth={3} /></button>
          <button type="button" className="tl yellow" aria-label="Minimise window" onClick={() => setMode("min")}><Minus size={8} strokeWidth={3} /></button>
          <button type="button" className="tl green" aria-label={full ? "Exit full screen" : "Enter full screen"} onClick={() => setMode(full ? "open" : "full")}><Maximize2 size={7} strokeWidth={3} /></button>
        </div>
        <span className="mac-title">BellAI — Today</span>
      </div>
      <div className="mac-app">
        <aside className="mac-side">
          <span className="side-item on"><House size={15} />Today</span>
          <span className="side-item"><Users size={15} />People</span>
          <span className="side-item"><Phone size={15} />Calls</span>
                    <span className="side-user"><span>P</span>Priya</span>
        </aside>
        <div className="mac-main">
          <p className="mac-hello">Good morning, Priya</p>
          <p className="mac-sum"><i />1 reminder needs you. Everything else is on track.</p>
          <MacCard title="Needs your attention" icon={<BellRing size={14} />} rows={ROWS.attention} tone="attention" />
          <MacCard title="Coming up" icon={<CalendarDays size={14} />} rows={ROWS.upcoming} />
          <MacCard title="Recent calls" icon={<Clock size={14} />} rows={ROWS.calls} />
        </div>
      </div>
    </motion.div>
  );

  return (
    <div className="mac-stage">
      <AnimatePresence mode="popLayout">
        {mode === "open" && win(false)}
        {mode === "closed" && (
          <motion.div key="closed" className="mac-empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <p>You closed the dashboard.</p>
            <button type="button" className="btn primary" onClick={() => setMode("open")}>Open it again</button>
          </motion.div>
        )}
        {mode === "min" && (
          <motion.div key="dock" className="mac-dock-wrap" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <p>Minimised to the dock. Click the BellAI icon to bring it back.</p>
            <div className="mac-dock">
              <span className="dock-icon muted" />
              <span className="dock-icon muted two" />
              <motion.button type="button" className="dock-icon app" aria-label="Restore BellAI window" onClick={() => setMode("open")}
                initial={{ y: 0 }} animate={{ y: [0, -14, 0, -8, 0] }} transition={{ duration: 0.9, delay: 0.25 }}>
                <BellRing size={22} />
              </motion.button>
              <span className="dock-icon muted three" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {mode === "full" && (
          <motion.div key="overlay" className="mac-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setMode("open")}>
            <div onClick={(e) => e.stopPropagation()} className="mac-overlay-inner">{win(true)}</div>
          </motion.div>
        )}
      </AnimatePresence>
      {mode === "full" && <div className="mac-placeholder" aria-hidden="true" />}
    </div>
  );
}

function MacCard({ title, icon, rows, tone = "" }: { title: string; icon: React.ReactNode; rows: typeof ROWS.upcoming; tone?: string }) {
  return (
    <div className={`mac-card ${tone}`}>
      <small>{icon}{title}</small>
      {rows.map((r, i) => (
        <motion.div key={r.title} className="mac-row" initial={{ opacity: 0, x: -8 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: 0.15 + i * 0.08 }}>
          <span><b>{r.title}</b><em>{r.sub}</em></span>
          <i className={`chip ${r.tone}`}>{r.tone === "ok" && <Check size={11} strokeWidth={3} />}{r.chip}</i>
        </motion.div>
      ))}
    </div>
  );
}
