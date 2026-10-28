// API client — all calls go through the Vite dev proxy (/api → :8000).
const BASE = "/api/v1";

export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let code = `HTTP_${res.status}`;
    let message = res.statusText || "Request failed";
    try {
      const body = await res.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(code, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/health"),
  dashboard: () => request<import("./types").DashboardSummary>("/dashboard/summary"),
  bins: (params: Record<string, string> = {}) =>
    request<import("./types").BinList>(`/bins?${new URLSearchParams(params)}`),
  binReadings: (binId: string, limit = 48) =>
    request<import("./types").ReadingList>(`/bins/${binId}/readings?limit=${limit}`),
  postReading: (binId: string, fill: number) =>
    request<import("./types").Reading>(`/bins/${binId}/readings`, {
      method: "POST",
      body: JSON.stringify({ fill_percent: fill, source: "simulator" }),
    }),
  simulate: (steps = 1) =>
    request<{ simulated: boolean; bins_updated: number }>("/demo/simulate", {
      method: "POST",
      body: JSON.stringify({ steps }),
    }),
  resetDemo: () => request<{ reset: boolean; bins: number }>("/demo/reset", { method: "POST" }),
  trucks: () => request<import("./types").Truck[]>("/fleet/trucks"),
  depots: () => request<import("./types").Depot[]>("/fleet/depots"),
  runOptimization: (payload: object) =>
    request<import("./types").OptimizationRun>("/optimization/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runs: (limit = 10) => request<import("./types").RunList>(`/optimization/runs?limit=${limit}`),
  run: (runId: string) => request<import("./types").OptimizationRun>(`/optimization/runs/${runId}`),
  forecast: (binId: string, horizonHours = 24) =>
    request<import("./types").Forecast>(
      `/forecasts?${new URLSearchParams({ bin_id: binId, horizon_hours: String(horizonHours) })}`
    ),
  classifications: (limit = 50) =>
    request<import("./types").ClassificationList>(`/recycling/classifications?limit=${limit}`),
  classify: (payload: object) =>
    request<import("./types").Classification>("/recycling/classifications", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recyclingSummary: () => request<import("./types").RecyclingSummary>("/recycling/summary"),
  alerts: (params: Record<string, string> = {}) =>
    request<import("./types").AlertList>(`/alerts?${new URLSearchParams(params)}`),
  acknowledgeAlert: (id: number) =>
    request<import("./types").Alert>(`/alerts/${id}/acknowledge`, { method: "POST" }),
  resolveAlert: (id: number) =>
    request<import("./types").Alert>(`/alerts/${id}/resolve`, { method: "POST" }),
  settings: () => request<import("./types").Settings>("/settings"),
  patchSettings: (payload: object) =>
    request<import("./types").Settings>("/settings", { method: "PATCH", body: JSON.stringify(payload) }),
};
