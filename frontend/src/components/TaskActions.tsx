"use client";

import { useState } from "react";
import { api, errorText } from "@/lib/api";
import { needsAttention } from "@/lib/format";
import type { Task } from "@/lib/types";

/** The buttons a caregiver can use on a reminder, depending on its status. */
export function TaskActions({ task, onChange }: { task: Task; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = (action: () => Promise<unknown>) => async () => {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChange();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const callNow = run(() => api.callNow(task.id));
  const resolve = run(() => api.resolveTask(task.id));
  const reset = run(() => api.updateTask(task.id, { status: "pending" }));

  return (
    <div className="actions">
      {task.status === "calling" ? (
        <button className="btn ghost" disabled={busy} onClick={reset} title="Only if a call looks stuck. Puts the reminder back on schedule.">
          Reset call
        </button>
      ) : task.status === "completed" ? null : (
        <button className="btn" disabled={busy} onClick={callNow} title={needsAttention(task.status) ? "Try them once more, with a fresh set of tries" : "Call them right now instead of waiting"}>
          {needsAttention(task.status) ? "Call again" : "Call now"}
        </button>
      )}
      {needsAttention(task.status) && (
        <button className="btn primary" disabled={busy} onClick={resolve} title="You have checked on them. A repeating reminder carries on as normal.">
          Mark handled
        </button>
      )}
      {error && <span className="error small">{error}</span>}
    </div>
  );
}
