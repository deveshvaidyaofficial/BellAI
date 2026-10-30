import { OUTCOME_LABEL, STATUS_HELP, STATUS_LABEL } from "@/lib/format";
import type { CallOutcome, TaskStatus } from "@/lib/types";

export function StatusBadge({ status }: { status: TaskStatus }) {
  return <span className={`badge badge-${status}`} title={STATUS_HELP[status]}>{STATUS_LABEL[status]}</span>;
}

export function OutcomeBadge({ outcome, status }: { outcome: CallOutcome | null; status: string }) {
  if (!outcome) return <span className="badge badge-calling">{status === "queued" ? "Ringing" : status}</span>;
  return <span className={`badge badge-outcome-${outcome}`}>{OUTCOME_LABEL[outcome]}</span>;
}
