"use client";

import { useEffect, useState } from "react";
import { api, parseUtc } from "@/lib/api";
import type { Elder, Task } from "@/lib/types";

export default function Dashboard() {
  const [elders, setElders] = useState<Elder[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    Promise.all([api.listElders(), api.listTasks()])
      .then(([e, t]) => { setElders(e); setTasks(t); setError(null); })
      .catch((e) => setError(String(e)));

  useEffect(() => {
    load();
    const id = setInterval(load, 5000); // TODO(frontend): replace polling with SSE/websocket if needed
    return () => clearInterval(id);
  }, []);

  const callNow = async (taskId: number) => {
    await api.callNow(taskId).catch((e) => setError(String(e)));
    load();
  };

  return (
    <>
      <h1>Dashboard</h1>
      {error && <p className="error">Backend unreachable: {error}</p>}
      {elders.length === 0 && <p className="muted">No elders yet — add one to get started.</p>}

      {elders.map((elder) => (
        <section key={elder.id} className="card">
          <h2>{elder.name}</h2>
          <p className="muted">{elder.phone} · {elder.language} · calls {elder.call_window_start}–{elder.call_window_end}</p>
          <table>
            <thead>
              <tr><th>Reminder</th><th>Type</th><th>Next</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {tasks.filter((t) => t.elder_id === elder.id).map((t) => (
                <tr key={t.id}>
                  <td>{t.title}</td>
                  <td>{t.type}</td>
                  <td>{parseUtc(t.scheduled_at).toLocaleString()}</td>
                  <td><span className="status">{t.status}</span></td>
                  <td><button onClick={() => callNow(t.id)}>Call now</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </>
  );
}
