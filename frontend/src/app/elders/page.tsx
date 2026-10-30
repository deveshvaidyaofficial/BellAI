"use client";

import Link from "next/link";
import { useRef } from "react";
import { RemovePersonButton } from "@/components/RemovePersonButton";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { LANGUAGES, needsAttention } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";
import { Skeleton } from "@/components/Skeleton";

const load = () => Promise.all([api.listElders(), api.listTasks()]);

export default function Elders() {
  const { data, error, reload } = usePolling(load, 10000);
  const addPerson = useRef<HTMLAnchorElement>(null);
  if (!data) return error ? <p className="error">{error}</p> : <Skeleton />;
  const [elders, tasks] = data;

  return (
    <>
      <div className="card-head">
        <h1>People</h1>
        <Link href="/elders/new" className="btn primary" ref={addPerson}>Add a person</Link>
      </div>
      {elders.length === 0 && <p className="muted">No one added yet.</p>}
      <ul className="grid">
        {elders.map((e) => {
          const mine = tasks.filter((t) => t.elder_id === e.id);
          const flagged = mine.find((t) => needsAttention(t.status));
          return (
            <li key={e.id} className="person">
              <Link href={`/elders/${e.id}`} className="card tile">
                <h2>{e.name}</h2>
                <p className="muted small">{e.phone} · {LANGUAGES[e.language] ?? e.language}</p>
                <p className="small">{mine.length} reminder{mine.length === 1 ? "" : "s"}</p>
                {flagged && <StatusBadge status={flagged.status} />}
              </Link>
              <RemovePersonButton elder={e} onChange={reload} onRemoved={() => addPerson.current?.focus()} />
            </li>
          );
        })}
      </ul>
    </>
  );
}
