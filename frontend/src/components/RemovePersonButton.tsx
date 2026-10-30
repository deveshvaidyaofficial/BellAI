"use client";

import { useRef, useState } from "react";
import { api, ApiError, errorText } from "@/lib/api";
import type { Elder } from "@/lib/types";

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
// Something already deleted (here or in another tab) counts as done.
const gone = (e: unknown) => {
  if (!(e instanceof ApiError && e.status === 404)) throw e;
};

class NewReminder extends Error {}

/**
 * "Remove" button plus a confirm dialog for one person (elder).
 * The API refuses to delete someone who still has reminders (409), so their
 * reminders are deleted first, then the person; their family contacts go with
 * them. Call history is kept by the backend.
 */
export function RemovePersonButton({ elder, onChange, onRemoved }: {
  elder: Elder;
  onChange: () => void; // refresh the list
  onRemoved: () => void; // after a successful removal (this button is about to unmount)
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const keep = useRef<HTMLButtonElement>(null);
  const removed = useRef(false);
  const working = useRef(false);
  const [linked, setLinked] = useState<{ tasks: number[]; contacts: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const titleId = `remove-${elder.id}-title`;
  const bodyId = `remove-${elder.id}-body`;
  const newReminderText = `${elder.name} got a new reminder while this was open. Check the updated count and confirm again.`;

  const loadLinked = async () => {
    const [tasks, contacts] = await Promise.all([api.listTasks(elder.id), api.listContacts(elder.id)]);
    setLinked({ tasks: tasks.map((t) => t.id), contacts: contacts.length });
  };

  const open = async () => {
    setLinked(null);
    setError(null);
    dialog.current?.showModal();
    keep.current?.focus();
    try {
      await loadLinked();
    } catch (e) {
      setError(errorText(e));
    }
  };

  const close = () => {
    if (!busy) dialog.current?.close();
  };

  const remove = async () => {
    if (!linked || working.current) return;
    working.current = true;
    setBusy(true);
    setError(null);
    try {
      // Fresh list, so we never delete a reminder the caregiver wasn't told about.
      const tasks = await api.listTasks(elder.id);
      if (tasks.some((t) => !linked.tasks.includes(t.id))) throw new NewReminder();
      for (const t of tasks) await api.deleteTask(t.id).catch(gone);
      await api.deleteElder(elder.id).catch(gone);
      removed.current = true; // this button is going away; onRemoved() picks the next focus
      dialog.current?.close();
      onChange();
      onRemoved();
    } catch (e) {
      const raced = e instanceof NewReminder || (e instanceof ApiError && e.status === 409);
      setError(raced ? newReminderText : errorText(e));
      if (dialog.current && !dialog.current.open) {
        dialog.current.showModal(); // keep the error visible
        keep.current?.focus();
      }
      onChange(); // some reminders may be gone already; show the list as it is now
      loadLinked().catch(() => {}); // and keep the counts here true
    } finally {
      working.current = false;
      setBusy(false);
    }
  };

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className="btn ghost small person-remove"
        onClick={open}
        aria-label={`Remove ${elder.name}`}
      >
        Remove
      </button>
      <dialog
        ref={dialog}
        className="confirm"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        onCancel={(e) => busy && e.preventDefault()}
        onClose={() => removed.current || trigger.current?.focus()}
        onClick={(e) => e.target === dialog.current && close()} // backdrop only; the padding lives on the inner div
      >
        <div className="confirm-body">
          <h2 id={titleId}>Remove {elder.name}?</h2>
          <div id={bodyId}>
            {!linked && !error && <p className="muted">Checking {elder.name}&apos;s reminders and contacts…</p>}
            {linked && (
              <>
                <p>
                  BellAI will stop calling {elder.name}. Their profile
                  {linked.contacts > 0 && <> and {plural(linked.contacts, "family contact")}</>}
                  {linked.tasks.length > 0 && <>, plus {plural(linked.tasks.length, "reminder")},</>} will be deleted.
                </p>
                <p className="muted small">Past calls stay in Calls. This can&apos;t be undone.</p>
              </>
            )}
          </div>
          {error && <p className="error" role="alert">{error}</p>}
          <div className="actions">
            {/* aria-disabled while busy keeps focus on this button instead of dropping it to <body> */}
            <button type="button" className="btn danger" onClick={remove} disabled={!linked} aria-disabled={busy}>
              {busy ? "Removing…" : `Remove ${elder.name}`}
            </button>
            <button ref={keep} type="button" className="btn ghost" onClick={close} disabled={busy}>
              Keep
            </button>
          </div>
        </div>
      </dialog>
    </>
  );
}
