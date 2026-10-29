// The only place the frontend talks to the backend.
import type {
  CallLog,
  Contact,
  ContactCreate,
  Elder,
  ElderCreate,
  ElderUpdate,
  Task,
  TaskCreate,
  TaskUpdate,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, `Can't reach the BellAI server at ${BASE}. Is the backend running?`);
  }
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  return (res.status === 204 ? undefined : await res.json()) as T;
}

/** FastAPI errors are {detail: string} or {detail: [{msg, loc}]} for validation. */
async function errorMessage(res: Response): Promise<string> {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.at(-1) ?? ""}: ${d.msg}`).join("; ");
  } catch {}
  return `Request failed (${res.status})`;
}

const send = <T>(method: string, path: string, body?: unknown) =>
  request<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });

export const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

export const api = {
  listElders: () => request<Elder[]>("/api/elders"),
  getElder: (id: number) => request<Elder>(`/api/elders/${id}`),
  createElder: (body: ElderCreate) => send<Elder>("POST", "/api/elders", body),
  updateElder: (id: number, body: ElderUpdate) => send<Elder>("PATCH", `/api/elders/${id}`, body),
  listContacts: (elderId: number) => request<Contact[]>(`/api/elders/${elderId}/contacts`),
  addContact: (elderId: number, body: ContactCreate) => send<Contact>("POST", `/api/elders/${elderId}/contacts`, body),

  listTasks: (elderId?: number) => request<Task[]>(`/api/tasks${elderId ? `?elder_id=${elderId}` : ""}`),
  getTask: (id: number) => request<Task>(`/api/tasks/${id}`),
  createTask: (body: TaskCreate) => send<Task>("POST", "/api/tasks", body),
  updateTask: (id: number, body: TaskUpdate) => send<Task>("PATCH", `/api/tasks/${id}`, body),
  deleteTask: (id: number) => send<void>("DELETE", `/api/tasks/${id}`),
  callNow: (id: number) => send<CallLog>("POST", `/api/tasks/${id}/call-now`),
  resolveTask: (id: number) => send<Task>("POST", `/api/tasks/${id}/resolve`),

  listCalls: (taskId?: number) => request<CallLog[]>(`/api/calls${taskId ? `?task_id=${taskId}` : ""}`),
};
