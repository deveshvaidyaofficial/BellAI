"use client";

import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { Icon } from "@/components/Icons";
import { Skeleton } from "@/components/Skeleton";
import { TaskTable } from "@/components/TaskTable";
import { api } from "@/lib/api";
import { needsAttention } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";

const loadAll = async () => {
  const [elders, tasks] = await Promise.all([api.listElders(), api.listTasks()]);
  const contacts = (await Promise.all(elders.map((e) => api.listContacts(e.id)))).flat();
  return { elders, tasks, contacts };
};

function greeting(name: string | undefined) {
  const h = new Date().getHours();
  const part = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
  const first = name && !/^\+?\d/.test(name) ? name.split(" ")[0] : "";
  return first ? `${part}, ${first}` : part;
}

export default function Dashboard() {
  const { caregiver } = useAuth();
  const { data, error, reload } = usePolling(loadAll);
  if (!data) return error ? <p className="error">{error}</p> : <Skeleton rows={4} />;

  const { elders, tasks, contacts } = data;
  const attention = tasks.filter((t) => needsAttention(t.status));
  const next = tasks
    .filter((t) => t.status === "calling" || t.status === "pending" || t.status === "snoozed")
    .sort((a, b) => (a.status === "calling" ? -1 : b.status === "calling" ? 1 : a.scheduled_at.localeCompare(b.scheduled_at)))
    .slice(0, 6);

  const steps = [
    { done: elders.length > 0, title: "Add the person you care for", href: "/elders/new" },
    { done: contacts.length > 0, title: "Add a family contact", href: elders[0] ? `/elders/${elders[0].id}#contacts` : "/elders/new" },
    { done: tasks.length > 0, title: "Set the first reminder", href: "/tasks/new" },
  ];
  const setupLeft = steps.some((s) => !s.done);

  return (
    <div className="dash">
      {error && <p className="error">{error}</p>}

      <header className="dash-head">
        <div>
          <h1>{greeting(caregiver?.name)}</h1>
          <p className={`dash-summary ${attention.length ? "alert" : ""}`}>
            <span className="status-dot" />
            {setupLeft
              ? "Finish setting up and BellAI will start calling."
              : attention.length
                ? `${attention.length} reminder${attention.length === 1 ? "" : "s"} need${attention.length === 1 ? "s" : ""} you.`
                : "All good. Nothing needs you."}
          </p>
        </div>
      </header>

      {setupLeft && (
        <ol className="card setup-steps">
          {steps.map((s, i) => {
            const isNext = s === steps.find((x) => !x.done);
            return (
              <li key={s.title} className={s.done ? "done" : isNext ? "next" : ""}>
                <span className="step-mark">{s.done ? <Icon name="check" className="icon sm" /> : i + 1}</span>
                <b>{s.title}</b>
                {isNext && <Link href={s.href} className="btn primary">Start</Link>}
              </li>
            );
          })}
        </ol>
      )}

      {attention.length > 0 && (
        <section className="card attention">
          <h2>Needs you</h2>
          <TaskTable tasks={attention} elders={elders} onChange={reload} />
        </section>
      )}

      {elders.length > 0 && (
        <section className="card">
          <div className="card-head">
            <h2>Next calls</h2>
            <Link href="/calls" className="muted small">Call history →</Link>
          </div>
          <TaskTable tasks={next} elders={elders} onChange={reload} empty="Nothing scheduled yet." />
        </section>
      )}
    </div>
  );
}
