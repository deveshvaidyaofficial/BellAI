"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { BellLogo } from "../BellLogo";

const KEY = "bellai.splash";
// Runs before paint, so repeat visits and reduced-motion users never see the splash flash.
const SKIP = `try{if(sessionStorage.getItem("${KEY}")||matchMedia("(prefers-reduced-motion: reduce)").matches)document.documentElement.dataset.nosplash="1"}catch(e){}`;

/** Short branded loading screen, shown once per browser session on the landing page. */
export function Splash() {
  const [show, setShow] = useState(true);

  useEffect(() => {
    if (document.documentElement.dataset.nosplash) return setShow(false);
    try {
      sessionStorage.setItem(KEY, "1");
    } catch {}
    const id = setTimeout(() => setShow(false), 1500);
    return () => clearTimeout(id);
  }, []);

  return (
    <>
      <script dangerouslySetInnerHTML={{ __html: SKIP }} />
      <AnimatePresence>
        {show && (
          <motion.div
            className="splash"
            aria-hidden="true"
            exit={{ y: "-100%" }}
            transition={{ duration: 0.7, ease: [0.76, 0, 0.24, 1] }}
          >
            <div className="splash-mark">
              <span className="splash-ring" />
              <span className="splash-ring two" />
              <motion.span
                className="splash-bell"
                animate={{ rotate: [0, -16, 14, -10, 8, -4, 0] }}
                transition={{ duration: 0.9, delay: 0.15, ease: "easeInOut" }}
              >
                <BellLogo />
              </motion.span>
            </div>
            <div className="splash-word">
              {"BellAI".split("").map((c, i) => (
                <motion.span key={i} initial={{ y: "110%" }} animate={{ y: 0 }} transition={{ delay: 0.2 + i * 0.05, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}>
                  {c}
                </motion.span>
              ))}
            </div>
            <span className="splash-bar"><motion.i initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 1.2, ease: [0.65, 0, 0.35, 1] }} /></span>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
