"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { BatteryFull, BellRing, Check, Grid3x3, Mic, Phone, PhoneOff, Signal, Volume2, Wifi } from "lucide-react";
import { useEffect, useState } from "react";

type Stage = "incoming" | "talking" | "done";

const LINES: { who: "bell" | "her"; text: string }[] = [
  { who: "bell", text: "Good morning, Savitri! It’s time for your blood pressure tablet." },
  { who: "her", text: "Oh yes. The small white one?" },
  { who: "bell", text: "That’s right, from the box marked morning. Have you taken it?" },
  { who: "her", text: "Done. Thank you, dear." },
];

const STAGE_MS: Record<Stage, number> = { incoming: 3400, talking: 9000, done: 3400 };
const NEXT: Record<Stage, Stage> = { incoming: "talking", talking: "done", done: "incoming" };

/** An iPhone showing BellAI ringing, the conversation, and the result, on a loop. */
export function IPhoneCall() {
  const still = useReducedMotion();
  const [stage, setStage] = useState<Stage>("incoming");
  const [shown, setShown] = useState(0);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (still) return;
    const id = setTimeout(() => setStage(NEXT[stage]), STAGE_MS[stage]);
    return () => clearTimeout(id);
  }, [stage, still]);

  useEffect(() => {
    if (stage !== "talking") return setShown(0), setSeconds(0);
    const lines = setInterval(() => setShown((n) => Math.min(n + 1, LINES.length)), 1900);
    const clock = setInterval(() => setSeconds((s) => s + 1), 1000);
    setShown(1);
    return () => (clearInterval(lines), clearInterval(clock));
  }, [stage]);

  const current: Stage = still ? "talking" : stage;
  const visible = still ? LINES.length : shown;

  return (
    <div className="phone-demo">
    <div className="iphone" role="img" aria-label="An iPhone receiving a call from BellAI. BellAI reminds Savitri about her blood pressure tablet, she confirms, and her daughter Priya is told.">
      <div className="iphone-screen">
        <div className="iphone-status">
          <span className="st-time">8:00</span>
          <div className="island-slot">
            <motion.div
              className="island"
              initial={false}
              animate={{ width: current === "talking" ? 136 : 96 }}
              transition={{ type: "spring", stiffness: 320, damping: 30 }}
            >
              <AnimatePresence>
                {current === "talking" && (
                  <motion.span className="island-live" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ delay: 0.15 }}>
                    <span className="island-left"><Phone size={11} fill="currentColor" />{`0:${String(seconds).padStart(2, "0")}`}</span>
                    <span className="island-wave" aria-hidden="true"><i /><i /><i /><i /></span>
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.div>
          </div>
          <span className="iphone-icons st-icons"><Signal size={14} /><Wifi size={14} /><BatteryFull size={18} /></span>
        </div>

        <AnimatePresence mode="wait">
          {current === "incoming" && (
            <motion.div key="incoming" className="call-pane incoming" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.96 }}>
              <div className="caller">
                <span className="caller-sub">mobile · calling…</span>
                <b>BellAI</b>
              </div>
              <div className="ring-wrap">
                <span className="ring r1" /><span className="ring r2" /><span className="ring r3" />
                <span className="caller-avatar"><BellRing size={34} /></span>
              </div>
              <div className="call-buttons">
                <span className="round-btn"><span className="decline"><PhoneOff size={26} /></span>Decline</span>
                <span className="round-btn"><motion.span className="accept" animate={{ y: [0, -6, 0] }} transition={{ repeat: Infinity, duration: 1.2 }}><Phone size={26} /></motion.span>Accept</span>
              </div>
            </motion.div>
          )}

          {current === "talking" && (
            <motion.div key="talking" className="call-pane talking" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <div className="caller small">
                <b>BellAI</b>
                <span className="caller-sub">{`00:${String(seconds).padStart(2, "0")}`}</span>
              </div>
              <div className="transcript-live">
                <AnimatePresence initial={false}>
                  {LINES.slice(0, visible).map((l, i) => (
                    <motion.p key={i} className={`bubble ${l.who}`} initial={{ opacity: 0, y: 10, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ type: "spring", stiffness: 260, damping: 22 }}>
                      {l.text}
                    </motion.p>
                  ))}
                </AnimatePresence>
              </div>
              <div className="call-controls">
                <span><Mic size={20} /></span>
                <span><Grid3x3 size={20} /></span>
                <span><Volume2 size={20} /></span>
              </div>
              <span className="end-btn"><PhoneOff size={24} /></span>
            </motion.div>
          )}

          {current === "done" && (
            <motion.div key="done" className="call-pane done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <motion.span className="done-check" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 260, damping: 16, delay: 0.1 }}>
                <Check size={44} strokeWidth={2.6} />
              </motion.span>
              <b>Marked as taken</b>
              <span className="caller-sub">Blood pressure tablet · 8:01 am</span>
              <motion.div className="notif" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
                <span className="notif-icon"><BellRing size={14} /></span>
                <span><b>Priya has been told</b>Savitri took her 8:00 tablet.</span>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        <span className="home-bar" />
      </div>
    </div>
    <CallProgress stage={current} still={still} />
    </div>
  );
}

const PROGRESS: { stage: Stage; title: string; text: string }[] = [
  { stage: "incoming", title: "Rings on time", text: "8:00 am, inside call hours" },
  { stage: "talking", title: "A friendly chat", text: "She answers in her own words" },
  { stage: "done", title: "Family updated", text: "Logged and Priya is told" },
];

/** Three-step tracker under the phone, lit up in step with the call. */
function CallProgress({ stage, still }: { stage: Stage; still: boolean | null }) {
  return (
    <ol className="call-progress" aria-hidden="true">
      {PROGRESS.map((p, i) => {
        const active = !still && p.stage === stage;
        return (
          <li key={p.stage} className={active ? "on" : ""}>
            <span className="cp-n">{i + 1}</span>
            <span className="cp-text"><b>{p.title}</b>{p.text}</span>
            <span className="cp-bar">
              {active && <motion.i initial={{ width: "0%" }} animate={{ width: "100%" }} transition={{ duration: STAGE_MS[p.stage] / 1000, ease: "linear" }} />}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
