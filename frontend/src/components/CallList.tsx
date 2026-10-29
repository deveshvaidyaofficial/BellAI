import { parseUtc } from "@/lib/format";
import type { CallLog, Task } from "@/lib/types";
import { OutcomeBadge } from "./StatusBadge";

export function CallList({ calls, tasks, empty = "No calls yet." }: { calls: CallLog[]; tasks?: Task[]; empty?: string }) {
  if (calls.length === 0) return <p className="muted">{empty}</p>;
  const title = (id: number) => tasks?.find((t) => t.id === id)?.title ?? "Deleted reminder";

  return (
    <ul className="rows">
      {calls.map((c) => (
        <li key={c.id} className="row call">
          <div className="row-main">
            {tasks && <span className="row-title">{title(c.task_id)}</span>}
            <span className="muted small">{parseUtc(c.created_at).toLocaleString()}</span>
            {c.summary && <p className="summary">{c.summary}</p>}
            {c.delivery_result && (
              <span className={`small ${c.delivery_result === "sent" ? "ok" : "error"}`}>
                {c.delivery_result === "sent" ? "Family alerted" : `Family alert ${c.delivery_result}`}
              </span>
            )}
            {c.transcript && (
              <details>
                <summary className="small">Transcript</summary>
                <pre className="transcript">{c.transcript}</pre>
              </details>
            )}
          </div>
          <OutcomeBadge outcome={c.outcome} status={c.status} />
        </li>
      ))}
    </ul>
  );
}
