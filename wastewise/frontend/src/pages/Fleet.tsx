import { api } from "../api";
import { useApi } from "../hooks";
import { Badge, Card, EmptyState, ErrorState, PageHeader, Spinner, StatCard } from "../components/ui";

export default function Fleet() {
  const trucks = useApi(() => api.trucks(), []);
  const runs = useApi(() => api.runs(12), []);
  const settings = useApi(() => api.settings(), []);

  if (trucks.status === "loading" || runs.status === "loading")
    return <Spinner label="Loading fleet…" />;
  if (!trucks.data || !runs.data)
    return <ErrorState message={trucks.error || runs.error} />;

  const totalFuel = runs.data.items.reduce((s, r) => s + r.estimated_fuel_litres, 0);
  const totalCost = runs.data.items.reduce((s, r) => s + r.estimated_fuel_cost, 0);
  const avgSavings =
    runs.data.items.filter((r) => r.savings_percent != null).length > 0
      ? (
          runs.data.items.reduce((s, r) => s + (r.savings_percent ?? 0), 0) /
          runs.data.items.filter((r) => r.savings_percent != null).length
        ).toFixed(1)
      : "—";

  return (
    <>
      <PageHeader
        title="Fleet & Fuel"
        subtitle="Trucks, capacities and fuel estimates from recorded optimization runs"
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Active trucks" value={trucks.data.length} tone="good" />
        <StatCard label="Recorded runs" value={runs.data.total} />
        <StatCard label="Fuel (all runs)" value={`${totalFuel.toFixed(1)} L`} hint={`≈ ₹${totalCost.toFixed(0)} @ ₹${settings.data?.fuel_price_per_litre ?? "—"}/L`} tone="warn" />
        <StatCard label="Avg savings" value={avgSavings === "—" ? "—" : `${avgSavings}%`} hint="vs priority-order baseline" tone="lime" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Trucks" subtitle="Demo fleet — assumptions labelled">
          <ul className="space-y-3">
            {trucks.data.map((t) => (
              <li key={t.id} className="rounded-xl border border-edge/50 bg-panel2/40 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-ink">{t.name}</p>
                    <p className="text-xs text-dim">{t.id} · {t.registration_label}</p>
                  </div>
                  <Badge value={t.fuel_type.toUpperCase()} />
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-panel px-3 py-2">
                    <dt className="text-dim">Capacity</dt>
                    <dd className="mt-0.5 font-bold tabular-nums text-ink">{t.capacity_litres.toLocaleString()} L</dd>
                  </div>
                  <div className="rounded-lg bg-panel px-3 py-2">
                    <dt className="text-dim">Consumption (assumed)</dt>
                    <dd className="mt-0.5 font-bold tabular-nums text-ink">{t.consumption_l_per_100km} L/100km</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] text-dim/60">
            ⚠ Fuel figures are planning estimates only — they exclude idling, congestion, road grade and payload variation.
          </p>
        </Card>

        <Card title="Run history" subtitle="Most recent optimization runs">
          {runs.data.items.length === 0 ? (
            <EmptyState title="No runs yet" hint="Run one from the Collection Planner" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-edge/60 text-left uppercase tracking-wider text-dim">
                    <th className="pb-2 pr-3 font-semibold">Run</th>
                    <th className="pb-2 pr-3 font-semibold">Status</th>
                    <th className="pb-2 pr-3 font-semibold">Bins</th>
                    <th className="pb-2 pr-3 font-semibold">km</th>
                    <th className="pb-2 pr-3 font-semibold">Fuel</th>
                    <th className="pb-2 font-semibold">Saved</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-edge/40">
                  {runs.data.items.map((r) => (
                    <tr key={r.run_id}>
                      <td className="py-2.5 pr-3">
                        <p className="text-ink">{r.run_id.slice(0, 12)}…</p>
                        <p className="text-dim/70">{new Date(r.started_at).toLocaleString()}</p>
                      </td>
                      <td className="py-2.5 pr-3"><Badge value={r.status} /></td>
                      <td className="py-2.5 pr-3 tabular-nums text-ink">{r.selected_count}</td>
                      <td className="py-2.5 pr-3 tabular-nums text-ink">{r.total_distance_km}</td>
                      <td className="py-2.5 pr-3 tabular-nums text-dim">{r.estimated_fuel_litres}L · ₹{r.estimated_fuel_cost}</td>
                      <td className="py-2.5 tabular-nums text-lime">{r.savings_percent != null ? `${r.savings_percent}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
