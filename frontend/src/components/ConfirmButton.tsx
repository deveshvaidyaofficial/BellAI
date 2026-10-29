"use client";

import { useState } from "react";

/** Two-step button for destructive actions: first click asks, second click does it. */
export function ConfirmButton({ label, confirmLabel, onConfirm, disabled }: {
  label: string;
  confirmLabel: string;
  onConfirm: () => void;
  disabled?: boolean;
}) {
  const [asking, setAsking] = useState(false);
  if (!asking) {
    return <button type="button" className="btn ghost" disabled={disabled} onClick={() => setAsking(true)}>{label}</button>;
  }
  return (
    <span className="actions">
      <button type="button" className="btn danger" disabled={disabled} onClick={() => { setAsking(false); onConfirm(); }}>{confirmLabel}</button>
      <button type="button" className="btn ghost" onClick={() => setAsking(false)}>Keep</button>
    </span>
  );
}
