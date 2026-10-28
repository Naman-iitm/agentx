import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { BinList } from "./types";

type Status = "loading" | "ready" | "error";

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string>("");
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    let alive = true;
    setStatus("loading");
    fetcher()
      .then((d) => {
        if (!alive) return;
        setData(d);
        setStatus("ready");
      })
      .catch((e: Error) => {
        if (!alive) return;
        setError(e.message);
        setStatus("error");
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadKey]);

  return { data, status, error, reload, setData };
}

export function useBins(params: Record<string, string> = {}) {
  return useApi<BinList>(() => api.bins(params), [JSON.stringify(params)]);
}
