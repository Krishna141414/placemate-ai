"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
  setData: (data: T) => void;
}

/** Load one endpoint on mount, with loading, error and a manual reload. */
export function useApi<T>(path: string | null, method: "GET" | "POST" = "GET"): ApiState<T> {
  const [data, setDataState] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [version, setVersion] = useState(0);
  const latest = useRef(0);

  useEffect(() => {
    if (path === null) return;
    const call = ++latest.current;
    api<T>(path, { method })
      .then((result) => {
        if (call !== latest.current) return;
        setDataState(result);
        setError(null);
      })
      .catch((err) => {
        if (call !== latest.current) return;
        setError(errorMessage(err));
      })
      .finally(() => {
        if (call === latest.current) setLoading(false);
      });
  }, [path, method, version]);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    setVersion((v) => v + 1);
  }, []);

  const setData = useCallback((value: T) => setDataState(value), []);

  return { data, error, loading, reload, setData };
}
