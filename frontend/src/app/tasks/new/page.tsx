"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, errorText } from "@/lib/api";
import { RECURRENCE_LABEL, TYPE_LABEL } from "@/lib/format";
import type { Elder, Recurrence, TaskType } from "@/lib/types";
import { Skeleton } from "@/components/Skeleton";

const pad = (n: number) => String(n).padStart(2, "0");
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const TITLE_PLACEHOLDER: Record<TaskType, string> = {
  medication: "BP tablet (Amlodipine)",
  appointment: "Eye check-up at City Hospital",
  meal: "Lunch",
  hydration: "Drink a glass of water",
  other: "Evening walk",
};

const STEP_DAYS: Record<Recurrence, number> = { none: 0, daily: 1, weekly: 7 };

/** First call time. A repeating reminder whose time already passed today starts next time round. */
function firstCall(date: string, time: string, recurrence: Recurrence): string {
  const at = new Date(`${date}T${time}`);
  while (STEP_DAYS[recurrence] && at.getTime() < Date.now()) at.setDate(at.getDate() + STEP_DAYS[recurrence]);
  return at.toISOString();
}

/** Medicine dose/food timing go into `details`, which Bell reads out on the call. */
function buildDetails(type: TaskType, f: FormData): string | null {
  const parts = [];
  if (type === "medication") {
    const dose = String(f.get("dose") || "").trim();
    const food = String(f.get("food") || "");
    if (dose) parts.push(dose);
    if (food) parts.push(food);
  }
  const notes = String(f.get("details") || "").trim();
  if (notes) parts.push(notes);
  return parts.join(", ") || null;
}

function NewTaskForm() {
  const router = useRouter();
  const preselected = useSearchParams().get("elder");
  const [elders, setElders] = useState<Elder[] | null>(null);
  const [type, setType] = useState<TaskType>("medication");
  const [times, setTimes] = useState<string[]>(["09:00"]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.listElders().then(setElders).catch((e) => setError(errorText(e)));
  }, []);

  const setTime = (i: number, v: string) => setTimes(times.map((t, j) => (j === i ? v : t)));

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const date = String(f.get("date"));
    const unique = Array.from(new Set(times.filter(Boolean)));
    if (unique.length === 0) return setError("Add at least one time.");

    setSaving(true);
    setError(null);
    try {
      // One reminder per time of day, so each dose is confirmed separately.
      const elderId = Number(f.get("elder_id"));
      const recurrence = f.get("recurrence") as Recurrence;
      for (const time of unique) {
        await api.createTask({
          elder_id: elderId,
          type,
          title: String(f.get("title")).trim(),
          details: buildDetails(type, f),
          scheduled_at: firstCall(date, time, recurrence),
          recurrence,
          max_attempts: Number(f.get("max_attempts")),
          retry_minutes: Number(f.get("retry_minutes")),
        });
      }
      router.push(`/elders/${elderId}`);
    } catch (err) {
      setError(errorText(err));
      setSaving(false);
    }
  };

  if (!elders) return error ? <p className="error">{error}</p> : <Skeleton />;
  if (elders.length === 0) {
    return <p>Add the person Bell should call first. <Link href="/elders/new" className="btn primary">Add a person</Link></p>;
  }

  return (
    <>
      <h1>Add a reminder</h1>
      <form onSubmit={onSubmit}>
        <label>
          For
          <select name="elder_id" defaultValue={preselected ?? undefined} required>
            {elders.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </label>

        <fieldset className="chips">
          <legend>What kind?</legend>
          {(Object.keys(TYPE_LABEL) as TaskType[]).map((t) => (
            <label key={t} className={`chip ${type === t ? "on" : ""}`}>
              <input type="radio" name="type" value={t} checked={type === t} onChange={() => setType(t)} />
              {TYPE_LABEL[t]}
            </label>
          ))}
        </fieldset>

        <label>What should Bell remind them about? <input name="title" placeholder={TITLE_PLACEHOLDER[type]} required /></label>

        {type === "medication" && (
          <div className="pair">
            <label>Dose <input name="dose" placeholder="1 tablet, 5 mg" /></label>
            <label>
              With food?
              <select name="food" defaultValue="">
                <option value="">—</option>
                <option>before food</option>
                <option>after food</option>
                <option>with food</option>
              </select>
            </label>
          </div>
        )}

        <label>Anything else Bell should say? <textarea name="details" rows={2} placeholder="Take it with a full glass of water" /></label>

        <div className="pair">
          <label>Starting <input name="date" type="date" defaultValue={today()} required /></label>
          <label>
            Repeat
            <select name="recurrence" defaultValue={type === "appointment" ? "none" : "daily"} key={type}>
              {(Object.keys(RECURRENCE_LABEL) as Recurrence[]).map((r) => <option key={r} value={r}>{RECURRENCE_LABEL[r]}</option>)}
            </select>
          </label>
        </div>

        <fieldset>
          <legend>At</legend>
          {times.map((t, i) => (
            <div key={i} className="time-row">
              <input type="time" value={t} onChange={(e) => setTime(i, e.target.value)} required aria-label={`Time ${i + 1}`} />
              {times.length > 1 && (
                <button type="button" className="btn ghost" onClick={() => setTimes(times.filter((_, j) => j !== i))}>Remove</button>
              )}
            </div>
          ))}
          <button type="button" className="btn ghost" onClick={() => setTimes([...times, "20:00"])}>+ Add another time</button>
        </fieldset>

        <details>
          <summary className="small">If they don't pick up</summary>
          <div className="pair">
            <label>Try up to <select name="max_attempts" defaultValue="3">{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select> times</label>
            <label>Every <select name="retry_minutes" defaultValue="10">{[5, 10, 15, 30].map((n) => <option key={n}>{n}</option>)}</select> minutes</label>
          </div>
        </details>

        {/* TODO(frontend): upload a prescription photo → vision model pre-fills this form. */}
        {error && <p className="error">{error}</p>}
        <button className="btn primary" disabled={saving}>
          {saving ? "Saving…" : times.length > 1 ? `Save ${times.length} reminders` : "Save reminder"}
        </button>
      </form>
    </>
  );
}

export default function NewTask() {
  return (
    <Suspense fallback={<Skeleton />}>
      <NewTaskForm />
    </Suspense>
  );
}
