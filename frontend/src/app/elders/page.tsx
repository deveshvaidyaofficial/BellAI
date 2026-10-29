"use client";

import Link from "next/link";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { LANGUAGES, needsAttention } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";

const load = () => Promise.all([api.listElders(), api.listTasks()]);

export default function Elders() {
  const { data, error } = usePolling(load, 10000);
  if (!data) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;
  const [elders, tasks] = data;

  return (
    <>
      <div className="card-head">
        <h1>People</h1>
        <Link href="/elders/new" className="btn primary">Add a person</Link>
      </div>
      {elders.length === 0 && <p className="muted">No one added yet.</p>}
      <ul className="grid">
        {elders.map((e) => {
          const mine = tasks.filter((t) => t.elder_id === e.id);
          const flagged = mine.find((t) => needsAttention(t.status));
          return (
            <li key={e.id}>
              <Link href={`/elders/${e.id}`} className="card tile">
                <h2>{e.name}</h2>
                <p className="muted small">{e.phone} · {LANGUAGES[e.language] ?? e.language}</p>
                <p className="small">{mine.length} reminder{mine.length === 1 ? "" : "s"}</p>
                {flagged && <StatusBadge status={flagged.status} />}
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );
}
