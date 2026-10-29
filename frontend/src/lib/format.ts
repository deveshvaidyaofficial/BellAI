import type { CallOutcome, Recurrence, TaskStatus, TaskType } from "./types";

/** Backend returns naive UTC timestamps; parse them as UTC. */
export const parseUtc = (iso: string) => new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);

const pad = (n: number) => String(n).padStart(2, "0");

/** UTC ISO from the API → value for <input type="datetime-local"> in the browser's timezone. */
export function toLocalInput(iso: string): string {
  const d = parseUtc(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** <input type="datetime-local"> value → UTC ISO for the API. */
export const fromLocalInput = (value: string) => new Date(value).toISOString();

export function when(iso: string): string {
  const d = parseUtc(iso);
  const today = new Date();
  const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
  const time = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (d.toDateString() === today.toDateString()) return `Today, ${time}`;
  if (d.toDateString() === tomorrow.toDateString()) return `Tomorrow, ${time}`;
  return d.toLocaleString([], { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

export const STATUS_LABEL: Record<TaskStatus, string> = {
  pending: "Scheduled",
  calling: "Calling now",
  completed: "Done",
  snoozed: "Snoozed",
  needs_help: "Needs help",
  missed: "Missed",
};

export const OUTCOME_LABEL: Record<CallOutcome, string> = {
  completed: "Confirmed",
  later: "Asked to call later",
  needs_help: "Needs help",
  no_answer: "No answer",
};

export const TYPE_LABEL: Record<TaskType, string> = {
  medication: "Medicine",
  appointment: "Appointment",
  meal: "Meal",
  hydration: "Water",
  other: "Other",
};

export const RECURRENCE_LABEL: Record<Recurrence, string> = {
  none: "Once",
  daily: "Every day",
  weekly: "Every week",
};

export const LANGUAGES: Record<string, string> = { en: "English", hi: "Hindi", mr: "Marathi" };

export const needsAttention = (s: TaskStatus) => s === "needs_help" || s === "missed";

/** Whether a reminder will be called again (finished one-off reminders won't). */
export const hasNextCall = (t: { status: TaskStatus; recurrence: Recurrence }) =>
  t.status !== "completed" && !(t.recurrence === "none" && needsAttention(t.status));

export const callWindow = (start: string, end: string) => (start === end ? "any time" : `${start}–${end}`);

/** Loose E.164 check: + then 8–15 digits. Spaces and dashes are stripped first. */
export const normalizePhone = (raw: string) => raw.replace(/[\s()-]/g, "");
export const isValidPhone = (raw: string) => /^\+[1-9]\d{7,14}$/.test(normalizePhone(raw));
