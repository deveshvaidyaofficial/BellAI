"use client";

import Link from "next/link";
import { hasNextCall, RECURRENCE_LABEL, TYPE_LABEL, when } from "@/lib/format";
import type { Elder, Task } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";
import { TaskActions } from "./TaskActions";

export function TaskTable({
  tasks,
  elders,
  onChange,
  empty = "No reminders.",
}: {
  tasks: Task[];
  elders?: Elder[];
  onChange: () => void;
  empty?: string;
}) {
  if (tasks.length === 0) return <p className="muted">{empty}</p>;
  const elderName = (id: number) => elders?.find((e) => e.id === id)?.name;

  return (
    <ul className="rows">
      {tasks.map((t) => (
        <li key={t.id} className="row">
          <div className="row-main">
            <Link href={`/tasks/${t.id}`} className="row-title">{t.title}</Link>
            <span className="muted small">
              {elders && <>{elderName(t.elder_id)} · </>}
              {TYPE_LABEL[t.type]} · {RECURRENCE_LABEL[t.recurrence]}
              {hasNextCall(t) && <> · next {when(t.scheduled_at)}</>}
              {t.attempts > 0 && hasNextCall(t) && <> · attempt {t.attempts}/{t.max_attempts}</>}
            </span>
          </div>
          <StatusBadge status={t.status} />
          <TaskActions task={t} onChange={onChange} />
        </li>
      ))}
    </ul>
  );
}
