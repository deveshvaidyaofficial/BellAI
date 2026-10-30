"use client";

import { CallList } from "@/components/CallList";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { Skeleton } from "@/components/Skeleton";

const load = () => Promise.all([api.listCalls(), api.listTasks()]);

export default function Calls() {
  const { data, error } = usePolling(load);
  if (!data) return error ? <p className="error">{error}</p> : <Skeleton />;
  const [calls, tasks] = data;

  return (
    <>
      <h1>Call history</h1>
      <section className="card">
        <CallList calls={calls} tasks={tasks} />
      </section>
    </>
  );
}
