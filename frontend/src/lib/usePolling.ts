"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorText } from "./api";

/**
 * Load data now and every `intervalMs`, so call statuses update without a refresh.
 * TODO(frontend): swap for SSE/websocket if polling gets heavy.
 */
export function usePolling<T>(load: () => Promise<T>, intervalMs = 5000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadRef = useRef(load);
  loadRef.current = load;

  const reload = useCallback(async () => {
    try {
      setData(await loadRef.current());
      setError(null);
    } catch (e) {
      setError(errorText(e));
    }
  }, []);

  useEffect(() => {
    reload();
    const id = setInterval(reload, intervalMs);
    return () => clearInterval(id);
  }, [reload, intervalMs]);

  return { data, error, reload };
}
