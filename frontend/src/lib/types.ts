// SHARED CONTRACT — mirrors backend/app/schemas.py. Change both together.

export type TaskType = "medication" | "appointment" | "meal" | "hydration" | "other";
export type Recurrence = "none" | "daily" | "weekly";
export type TaskStatus = "pending" | "calling" | "completed" | "snoozed" | "needs_help" | "missed";
export type CallOutcome = "completed" | "later" | "needs_help" | "no_answer";

export interface ElderCreate {
  name: string;
  phone: string;
  language?: string;
  timezone?: string;
  call_window_start?: string;
  call_window_end?: string;
  notes?: string | null;
}

export interface Elder extends Required<ElderCreate> {
  id: number;
  created_at: string;
}

export type ElderUpdate = Partial<ElderCreate>;

export interface ContactCreate {
  name: string;
  phone: string;
  relation?: string | null;
  notify_on_missed?: boolean;
}

export interface Contact extends ContactCreate {
  id: number;
  elder_id: number;
}

export interface TaskCreate {
  elder_id: number;
  type: TaskType;
  title: string;
  details?: string | null;
  scheduled_at: string; // ISO 8601; backend stores UTC
  recurrence?: Recurrence;
  max_attempts?: number;
  retry_minutes?: number;
}

export interface Task extends Required<TaskCreate> {
  id: number;
  status: TaskStatus;
  attempts: number;
  created_at: string;
}

// The only status a client may set is "pending" (reopen / reset a stuck call).
export type TaskUpdate = Partial<Omit<TaskCreate, "elder_id">> & { status?: "pending" };

export interface CallLog {
  id: number;
  task_id: number;
  bolna_call_id: string | null;
  status: string;
  outcome: CallOutcome | null;
  transcript: string | null;
  summary: string | null;
  delivery_result?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Caregiver {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  created_at: string;
}

export interface OtpRequest {
  phone: string;
}

export interface OtpRequestResponse {
  ok: boolean;
  code?: string | null;
}

export interface OtpVerify {
  phone: string;
  code: string;
}

export interface GoogleAuthRequest {
  id_token: string;
}

export interface AuthSession {
  token: string;
  caregiver: Caregiver;
}
