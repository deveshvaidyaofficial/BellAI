// The only place the frontend talks to the backend.
import type { CallLog, Contact, ContactCreate, Elder, ElderCreate, Task, TaskCreate } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

/** Backend returns naive UTC timestamps; parse them as UTC. */
export const parseUtc = (iso: string) => new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);

export const api = {
  listElders: () => request<Elder[]>("/api/elders"),
  createElder: (body: ElderCreate) => post<Elder>("/api/elders", body),
  listContacts: (elderId: number) => request<Contact[]>(`/api/elders/${elderId}/contacts`),
  addContact: (elderId: number, body: ContactCreate) => post<Contact>(`/api/elders/${elderId}/contacts`, body),

  listTasks: (elderId?: number) => request<Task[]>(`/api/tasks${elderId ? `?elder_id=${elderId}` : ""}`),
  createTask: (body: TaskCreate) => post<Task>("/api/tasks", body),
  callNow: (taskId: number) => post<CallLog>(`/api/tasks/${taskId}/call-now`),

  listCalls: (taskId?: number) => request<CallLog[]>(`/api/calls${taskId ? `?task_id=${taskId}` : ""}`),
};
