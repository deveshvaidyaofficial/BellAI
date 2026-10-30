"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useState } from "react";
import { CallList } from "@/components/CallList";
import { StatusBadge } from "@/components/StatusBadge";
import { TaskActions } from "@/components/TaskActions";
import { api, errorText } from "@/lib/api";
import { callWindow, fromLocalInput, hasNextCall, RECURRENCE_LABEL, toLocalInput, TYPE_LABEL, when } from "@/lib/format";
import type { Recurrence, TaskType } from "@/lib/types";
import { usePolling } from "@/lib/usePolling";
import { Skeleton } from "@/components/Skeleton";

export default function TaskPage() {
  const id = Number(useParams<{ id: string }>().id);
  const router = useRouter();
  const load = useCallback(async () => {
    const [task, calls] = await Promise.all([api.getTask(id), api.listCalls(id)]);
    return { task, calls, elder: await api.getElder(task.elder_id) };
  }, [id]);
  const { data, error, reload } = usePolling(load);
  const [editing, setEditing] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (!data) return error ? <p className="error">{error}</p> : <Skeleton />;
  const { task, calls, elder } = data;

  const save = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const scheduled = String(f.get("scheduled_at"));
    try {
      await api.updateTask(id, {
        type: f.get("type") as TaskType,
        title: String(f.get("title")).trim(),
        details: String(f.get("details") || "").trim() || null,
        recurrence: f.get("recurrence") as Recurrence,
        max_attempts: Number(f.get("max_attempts")),
        retry_minutes: Number(f.get("retry_minutes")),
        // Only send the time if it changed: rescheduling resets the retry count.
        ...(scheduled !== toLocalInput(task.scheduled_at) && { scheduled_at: fromLocalInput(scheduled) }),
      });
      setEditing(false);
      setFormError(null);
      reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  };

  const remove = async () => {
    try {
      await api.deleteTask(id);
      router.push(`/elders/${task.elder_id}`);
    } catch (err) {
      setFormError(errorText(err));
    }
  };

  return (
    <>
      <p><Link href={`/elders/${elder.id}`} className="muted small">← {elder.name}</Link></p>
      <div className="card-head">
        <h1>{task.title}</h1>
        <StatusBadge status={task.status} />
      </div>
      <p className="muted">
        {TYPE_LABEL[task.type]} · {RECURRENCE_LABEL[task.recurrence]}
        {hasNextCall(task) && <> · next {when(task.scheduled_at)}</>}
        {task.details && <><br />Bell will say: “{task.details}”</>}
      </p>
      <TaskActions task={task} onChange={reload} />
      {formError && <p className="error">{formError}</p>}

      <section className="card">
        <div className="card-head">
          <h2>Details</h2>
          <button className="btn" onClick={() => setEditing(!editing)}>{editing ? "Cancel" : "Edit"}</button>
        </div>
        {editing ? (
          <form onSubmit={save}>
            <label>
              Type
              <select name="type" defaultValue={task.type}>
                {(Object.keys(TYPE_LABEL) as TaskType[]).map((t) => <option key={t} value={t}>{TYPE_LABEL[t]}</option>)}
              </select>
            </label>
            <label>Reminder <input name="title" defaultValue={task.title} required /></label>
            <label>Details <textarea name="details" rows={2} defaultValue={task.details ?? ""} /></label>
            <div className="pair">
              <label>Next time <input name="scheduled_at" type="datetime-local" defaultValue={toLocalInput(task.scheduled_at)} required /></label>
              <label>
                Repeat
                <select name="recurrence" defaultValue={task.recurrence}>
                  {(Object.keys(RECURRENCE_LABEL) as Recurrence[]).map((r) => <option key={r} value={r}>{RECURRENCE_LABEL[r]}</option>)}
                </select>
              </label>
            </div>
            <div className="pair">
              <label>Tries if no answer <input name="max_attempts" type="number" min={1} max={10} defaultValue={task.max_attempts} /></label>
              <label>Minutes between tries <input name="retry_minutes" type="number" min={1} max={240} defaultValue={task.retry_minutes} /></label>
            </div>
            <div className="actions">
              <button className="btn primary">Save</button>
              <button type="button" className="btn danger" onClick={remove}>Delete reminder</button>
            </div>
          </form>
        ) : (
          <p className="muted small">
            Tries up to {task.max_attempts} times, {task.retry_minutes} min apart. Calls {elder.name} {callWindow(elder.call_window_start, elder.call_window_end)} ({elder.timezone}).
          </p>
        )}
      </section>

      <section className="card">
        <h2>Call history</h2>
        <CallList calls={calls} />
      </section>
    </>
  );
}
