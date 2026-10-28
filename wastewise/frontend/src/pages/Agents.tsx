import { useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks";
import { Badge, Card, EmptyState, ErrorState, PageHeader, Spinner } from "../components/ui";
import type { OptimizationRun } from "../types";

const FLOW = ["load_snapshot", "bin_agent", "prediction_agent", "route_agent", "fuel_agent", "recycling_agent", "persist_result"];

export default function Agents() {
  const runs = useApi(() => api.runs(8), []);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const detail = useApi(
    () => (selectedRun ? api.run(selectedRun) : Promise.resolve(null)),
    [selectedRun]
  );

  if (runs.status === "loading") return <Spinner label="Loading agent activity…" />;
  if (runs.status === "error" || !runs.data)
    return <ErrorState message={runs.error} onRetry={runs.reload} />;

  const activeRunId = selectedRun ?? runs.data.items[0]?.run_id ?? null;
  const run: OptimizationRun | null = detail.data;

  return (
    <>
      <PageHeader
        title="Agent Activity"
        subtitle="Every optimization run is a traceable LangGraph workflow — status, timing and decisions per agent"
      />

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        {/* run list */}
        <Card title="Runs" subtitle={`${runs.data.total} recorded`}>
          {runs.data.items.length === 0 ? (
            <EmptyState title="No runs yet" hint="Run one from the Collection Planner" />
          ) : (
            <ul className="space-y-2">
              {runs.data.items.map((r) => (
                <li key={r.run_id}>
                  <button
                    onClick={() => setSelectedRun(r.run_id)}
                    className={`w-full rounded-xl border px-3 py-2.5 text-left transition-colors ${
                      activeRunId === r.run_id
                        ? "border-lime/40 bg-lime/5"
                        : "border-edge/50 bg-panel2/40 hover:border-peri/30"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-[11px] text-dim">{r.run_id}</span>
                      <Badge value={r.status} />
                    </div>
                    <p className="mt-1 text-[11px] text-dim/70">
                      {new Date(r.started_at).toLocaleString()} · {r.selected_count} bins · {r.total_distance_km} km
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* detail */}
        <div className="space-y-4">
          {detail.status === "loading" ? (
            <Spinner label="Loading run detail…" />
          ) : detail.status === "error" ? (
            <ErrorState message={detail.error} onRetry={detail.reload} />
          ) : run ? (
            <>
              {/* pipeline */}
              <Card title="Workflow pipeline" subtitle={`${run.solver} · completed in ${run.duration_ms}ms`}>
                <div className="flex flex-wrap items-center gap-2">
                  {FLOW.map((name, i) => {
                    const a = run.agents.find((x) => x.agent_name === name);
                    const isPersist = name === "persist_result";
                    const status = isPersist ? "success" : a?.status ?? "skipped";
                    return (
                      <div key={name} className="flex items-center gap-2">
                        <div
                          className={`flex flex-col items-center gap-1 rounded-xl border px-3 py-2 ${
                            status === "success"
                              ? "border-normal/30 bg-normal/5"
                              : status === "partial"
                                ? "border-warning/30 bg-warning/5"
                                : status === "failed"
                                  ? "border-critical/30 bg-critical/5"
                                  : "border-edge"
                          }`}
                        >
                          <span className="text-[10px] font-semibold text-ink">{name}</span>
                          <span className="text-[10px] tabular-nums text-dim">
                            {isPersist ? "saved" : a ? `${a.duration_ms}ms` : "—"}
                          </span>
                        </div>
                        {i < FLOW.length - 1 && <span className="text-dim/40">→</span>}
                      </div>
                    );
                  })}
                </div>
              </Card>

              {/* agent cards */}
              <div className="grid gap-3 sm:grid-cols-2">
                {run.agents.map((a) => (
                  <Card key={a.agent_name}>
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-bold text-ink">⬡ {a.agent_name}</p>
                      <Badge value={a.status} />
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-dim">{a.summary}</p>
                    {a.reasons.length > 0 && (
                      <div className="mt-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-dim/70">Decisions</p>
                        <ul className="mt-1 space-y-0.5">
                          {a.reasons.slice(0, 5).map((r, i) => (
                            <li key={i} className="text-[11px] text-dim">• {r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {a.warnings.length > 0 && (
                      <div className="mt-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-warning/80">Warnings</p>
                        <ul className="mt-1 space-y-0.5">
                          {a.warnings.slice(0, 4).map((w, i) => (
                            <li key={i} className="text-[11px] text-warning/90">⚠ {w}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <p className="mt-3 text-right text-[10px] tabular-nums text-dim/60">{a.duration_ms}ms</p>
                  </Card>
                ))}
              </div>
            </>
          ) : (
            <EmptyState title="Select a run" />
          )}
        </div>
      </div>
    </>
  );
}
