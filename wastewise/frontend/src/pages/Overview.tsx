import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useApi } from "../hooks";
import { BarList, DonutChart } from "../components/charts";
import { Button, Card, DemoTag, EmptyState, ErrorState, PageHeader, Spinner, StatCard } from "../components/ui";

export default function Overview() {
  const summary = useApi(() => api.dashboard(), []);
  const alerts = useApi(() => api.alerts({ status: "OPEN", limit: "6" }), []);
  const [busy, setBusy] = useState<string | null>(null);

  const simulate = async () => {
    setBusy("sim");
    try {
      await api.simulate(1);
      await Promise.all([summary.reload(), alerts.reload()]);
    } finally {
      setBusy(null);
    }
  };

  if (summary.status === "loading") return <Spinner label="Loading control tower…" />;
  if (summary.status === "error" || !summary.data)
    return <ErrorState message={summary.error} onRetry={summary.reload} />;

  const s = summary.data;
  const distribution = [
    { label: "Critical", value: s.bins_critical, color: "#fb7185" },
    { label: "Warning", value: s.bins_warning, color: "#fbbf24" },
    { label: "Normal", value: s.bins_normal, color: "#34d399" },
  ];

  return (
    <>
      <PageHeader
        title="Smart City Control Tower"
        subtitle="Live-simulation overview of bins, alerts and the latest optimization run"
        actions={
          <>
            <DemoTag>Simulated telemetry</DemoTag>
            <Button variant="secondary" onClick={simulate} disabled={busy !== null}>
              {busy === "sim" ? "Simulating…" : "⚡ Simulate tick"}
            </Button>
            <Link to="/planner">
              <Button>Run Optimization</Button>
            </Link>
          </>
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Active bins"
          value={s.bins_total}
          hint={s.bins_stale > 0 ? `${s.bins_stale} stale sensor${s.bins_stale > 1 ? "s" : ""}` : "all sensors live"}
          tone={s.bins_stale > 0 ? "warn" : "good"}
        />
        <StatCard label="Avg fill" value={`${s.avg_fill_percent}%`} tone={s.avg_fill_percent > 80 ? "bad" : s.avg_fill_percent > 65 ? "warn" : "good"} />
        <StatCard label="Critical bins" value={s.bins_critical} tone={s.bins_critical > 0 ? "bad" : "good"} hint={`${s.bins_warning} in warning`} />
        <StatCard label="Open alerts" value={s.open_alerts} tone={s.open_alerts > 0 ? "warn" : "good"} hint={`${s.critical_alerts} critical`} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Fill-level distribution" subtitle="All active bins by status">
          <DonutChart segments={distribution} centerValue={String(s.bins_total)} centerLabel="bins" />
        </Card>

        <Card title="Zones" subtitle="Average fill by zone">
          <BarList
            items={s.zones.map((z) => ({
              label: `${z.zone} · ${z.bins} bins`,
              value: z.avg_fill_percent,
              max: 100,
              right: `${z.avg_fill_percent}%${z.critical_count ? ` · ${z.critical_count} crit` : ""}`,
              color: z.critical_count > 0 ? "#fb7185" : z.avg_fill_percent > 70 ? "#fbbf24" : "#34d399",
            }))}
          />
        </Card>

        <Card
          title="Latest optimization run"
          subtitle={s.latest_run ? new Date(s.latest_run.started_at).toLocaleString() : "no runs yet"}
          right={s.latest_run ? <Link to="/agents" className="text-xs text-peri hover:underline">details →</Link> : undefined}
        >
          {s.latest_run ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${s.latest_run.status === "FEASIBLE" ? "bg-normal/15 text-normal" : "bg-warning/15 text-warning"}`}>
                  {s.latest_run.status}
                </span>
                <span className="text-xs text-dim">{s.latest_run.selected_count} bins selected</span>
              </div>
              <dl className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-panel2 px-2 py-3">
                  <dd className="text-lg font-bold tabular-nums text-ink">{s.latest_run.total_distance_km}</dd>
                  <dt className="text-[10px] uppercase tracking-wider text-dim">km</dt>
                </div>
                <div className="rounded-xl bg-panel2 px-2 py-3">
                  <dd className="text-lg font-bold tabular-nums text-ink">₹{s.latest_run.estimated_fuel_cost}</dd>
                  <dt className="text-[10px] uppercase tracking-wider text-dim">est. fuel</dt>
                </div>
                <div className="rounded-xl bg-panel2 px-2 py-3">
                  <dd className="text-lg font-bold tabular-nums text-lime">{s.latest_run.savings_percent ?? "—"}{s.latest_run.savings_percent != null ? "%" : ""}</dd>
                  <dt className="text-[10px] uppercase tracking-wider text-dim">saved</dt>
                </div>
              </dl>
              <Link to="/planner" className="block">
                <Button variant="secondary" className="w-full">Open Collection Planner</Button>
              </Link>
            </div>
          ) : (
            <EmptyState title="No optimization runs yet" hint="Run one from the Collection Planner" />
          )}
        </Card>
      </div>

      <Card
        className="mt-4"
        title="Open alerts"
        subtitle={`${s.open_alerts} unresolved`}
        right={<Link to="/alerts" className="text-xs text-peri hover:underline">all alerts →</Link>}
      >
        {alerts.status === "loading" ? (
          <Spinner />
        ) : alerts.data && alerts.data.items.length > 0 ? (
          <ul className="divide-y divide-edge/50">
            {alerts.data.items.map((a) => (
              <li key={a.id} className="flex items-center gap-3 py-2.5">
                <span className={`size-2 shrink-0 rounded-full ${a.severity === "CRITICAL" ? "bg-critical" : a.severity === "HIGH" ? "bg-warning" : "bg-peri"}`} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">{a.title}</p>
                  <p className="text-xs text-dim">{a.type} · {new Date(a.created_at).toLocaleTimeString()}</p>
                </div>
                <span className="shrink-0 text-[10px] font-bold uppercase tracking-wider text-dim">{a.severity}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No open alerts" hint="Everything looks calm" />
        )}
      </Card>
    </>
  );
}
