"use client";

import { useCallback, useEffect, useState } from "react";

type Loaded<T> = { data?: T; error?: string; loading: boolean };

export function messageOf(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}

/** Load data once and again on reload(). `load` must be a stable reference (module-level function). */
export function useLoad<T>(load: () => Promise<T>) {
  const [state, setState] = useState<Loaded<T>>({ loading: true });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    load().then(
      (data) => alive && setState({ data, loading: false }),
      (e) => alive && setState({ error: messageOf(e), loading: false }),
    );
    return () => {
      alive = false;
    };
  }, [load, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
