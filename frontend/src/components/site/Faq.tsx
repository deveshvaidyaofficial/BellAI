"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useId, useState } from "react";

/** Accordion: the whole row is the button, and the plus turns into a minus when open. */
export function Faq({ items }: { items: [string, string][] }) {
  const [open, setOpen] = useState<number | null>(0);
  const base = useId();

  return (
    <div className="faq">
      {items.map(([q, a], i) => {
        const isOpen = open === i;
        return (
          <div key={q} className={`faq-item ${isOpen ? "open" : ""}`}>
            <h3>
              <button type="button" aria-expanded={isOpen} aria-controls={`${base}-${i}`} onClick={() => setOpen(isOpen ? null : i)}>
                <span>{q}</span>
                <span className="pm" aria-hidden="true"><i /><i /></span>
              </button>
            </h3>
            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  id={`${base}-${i}`}
                  role="region"
                  className="faq-a"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                >
                  <p>{a}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
