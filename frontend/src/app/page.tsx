"use client";

import Link from "next/link";
import { CallList } from "@/components/CallList";
import { TaskTable } from "@/components/TaskTable";
import { api } from "@/lib/api";
import { needsAttention } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";

const loadAll = () => Promise.all([api.listElders(), api.listTasks(), api.listCalls()]);

export default function Dashboard() {
  const { data, error, reload } = usePolling(loadAll);
  if (!data) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;

  const [elders, tasks, calls] = data;
  const attention = tasks.filter((t) => needsAttention(t.status));
  const calling = tasks.filter((t) => t.status === "calling");
  const upcoming = tasks.filter((t) => t.status === "pending" || t.status === "snoozed").slice(0, 8);

  if (elders.length === 0) {
    return (
      <section className="empty">
        <h1>Welcome to BellAI</h1>
        <p className="lede">Add the person you care for, then set up their first reminder. Bell will call them at the right time and let you know how it went.</p>
        <Link href="/elders/new" className="btn primary">Add a person</Link>
      </section>
    );
  }

  return (
    <>
      {error && <p className="error">{error}</p>}
      <h1>Today</h1>

      {attention.length > 0 && (
        <section className="card attention">
          <h2>Needs your attention</h2>
          <TaskTable tasks={attention} elders={elders} onChange={reload} />
        </section>
      )}

      {calling.length > 0 && (
        <section className="card">
          <h2>Calling now</h2>
          <TaskTable tasks={calling} elders={elders} onChange={reload} />
        </section>
      )}

      <section className="card">
        <div className="card-head">
          <h2>Coming up</h2>
          <Link href="/tasks/new" className="btn">Add reminder</Link>
        </div>
        <TaskTable tasks={upcoming} elders={elders} onChange={reload} empty="Nothing scheduled." />
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Recent calls</h2>
          <Link href="/calls" className="muted small">See all</Link>
        </div>
        <CallList calls={calls.slice(0, 5)} tasks={tasks} />
      </section>
    </>
  );
}
