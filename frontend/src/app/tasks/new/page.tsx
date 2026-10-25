"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Elder, Recurrence, TaskType } from "@/lib/types";

// TODO(frontend): medicine-specific fields (dose, before/after food), multiple times per day.
// Later: upload a prescription photo → vision model pre-fills this form.
export default function NewTask() {
  const router = useRouter();
  const [elders, setElders] = useState<Elder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.listElders().then(setElders).catch((e) => setError(String(e)));
  }, []);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setSaving(true);
    try {
      await api.createTask({
        elder_id: Number(f.get("elder_id")),
        type: f.get("type") as TaskType,
        title: String(f.get("title")),
        details: String(f.get("details") || "") || null,
        // datetime-local is the caregiver's local time; toISOString() converts to UTC.
        scheduled_at: new Date(String(f.get("scheduled_at"))).toISOString(),
        recurrence: f.get("recurrence") as Recurrence,
      });
      router.push("/");
    } catch (err) {
      setError(String(err));
      setSaving(false);
    }
  };

  return (
    <>
      <h1>Add reminder</h1>
      <form onSubmit={onSubmit}>
        <label>For
          <select name="elder_id" required>
            {elders.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </label>
        <label>Type
          <select name="type" defaultValue="medication">
            <option value="medication">Medication</option>
            <option value="appointment">Appointment</option>
            <option value="meal">Meal</option>
            <option value="hydration">Hydration</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>Reminder <input name="title" placeholder="Take BP tablet (Amlodipine 5mg)" required /></label>
        <label>Details <textarea name="details" rows={2} placeholder="After breakfast, with water" /></label>
        <label>When <input name="scheduled_at" type="datetime-local" required /></label>
        <label>Repeat
          <select name="recurrence" defaultValue="daily">
            <option value="none">Once</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </label>

        {error && <p className="error">{error}</p>}
        <button disabled={saving || elders.length === 0}>{saving ? "Saving…" : "Save"}</button>
      </form>
    </>
  );
}
