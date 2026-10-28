import { useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks";
import CityMap from "../components/CityMap";
import { Badge, Button, Card, DemoTag, EmptyState, ErrorState, PageHeader, Select, Spinner, StatCard } from "../components/ui";
import type { OptimizationRun } from "../types";

export default function Planner() {
  const depots = useApi(() => api.depots(), []);
  const trucks = useApi(() => api.trucks(), []);
  const bins = useApi(() => api.bins({ limit: "200" }), []);

  const [depotId, setDepotId] = useState("");
  const [truckId, setTruckId] = useState("");
  const [horizon, setHorizon] = useState("12");
  const [includePredicted, setIncludePredicted] = useState(true);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState("");
  const [result, setResult] = useState<OptimizationRun | null>(null);
  const [selectedBin, setSelectedBin] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setRunError("");
    setResult(null);
    try {
      const r = await api.runOptimization({
        depot_id: depotId || depots.data?.[0]?.id,
        truck_id: truckId || trucks.data?.[0]?.id,
        planning_horizon_hours: Number(horizon),
        include_predicted_overflow: includePredicted,
      });
      setResult(r);
    } catch (e) {
      setRunError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  if (depots.status === "loading" || trucks.status === "loading")
    return <Spinner label="Loading planner…" />;
  if (!depots.data || !trucks.data)
    return <ErrorState message={depots.error || trucks.error} />;

  const truck = trucks.data.find((t) => t.id === (truckId || trucks.data![0].id));
  const totalDemand = result?.selected_bins.reduce((s, b) => s + b.demand_litres, 0) ?? 0;

  return (
    <>
      <PageHeader
        title="Intelligent Collection Planning"
        subtitle="One click: select bins → optimize route → estimate fuel — five agents in a LangGraph workflow"
        actions={<DemoTag>estimates labelled</DemoTag>}
      />

      {/* ── controls ── */}
      <Card title="Run the multi-agent workflow" subtitle="Bin Agent → Prediction → Route (OR-Tools) → Fuel → Recycling">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-dim">
            Depot
            <Select
              value={depotId || depots.data[0]?.id || ""}
              onChange={setDepotId}
              options={depots.data.map((d) => ({ value: d.id, label: d.name.replace(" (Demo)", "") }))}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-dim">
            Truck
            <Select
              value={truckId || trucks.data[0]?.id || ""}
              onChange={setTruckId}
              options={trucks.data.map((t) => ({
                value: t.id,
                label: `${t.name} · ${t.capacity_litres}L · ${t.consumption_l_per_100km}L/100km`,
              }))}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-dim">
            Horizon
            <Select
              value={horizon}
              onChange={setHorizon}
              options={[6, 12, 24, 48].map((h) => ({ value: String(h), label: `${h} hours` }))}
            />
          </label>
          <label className="flex cursor-pointer items-center gap-2 pb-2.5 text-xs text-dim">
            <input
              type="checkbox"
              checked={includePredicted}
              onChange={(e) => setIncludePredicted(e.target.checked)}
              className="size-4 accent-lime"
            />
            include predicted overflow
          </label>
          <Button onClick={run} disabled={running} className="mb-0.5">
            {running ? "⟳ Agents working…" : "▶ Run Optimization"}
          </Button>
        </div>
        {runError && <p className="mt-3 rounded-lg bg-critical/10 px-3 py-2 text-xs text-critical">{runError}</p>}
      </Card>

      {running && (
        <div className="mt-4">
          <Card>
            <div className="flex flex-wrap items-center justify-center gap-3 py-6 text-sm text-dim">
              <AgentChip name="load_snapshot" active />
              <Arrow />
              <AgentChip name="bin_agent" active />
              <Arrow />
              <AgentChip name="prediction_agent" active />
              <Arrow />
              <AgentChip name="route_agent" active />
              <Arrow />
              <AgentChip name="fuel_agent" active />
              <Arrow />
              <AgentChip name="recycling_agent" active />
            </div>
          </Card>
        </div>
      )}

      {result && (
        <>
          {/* ── KPIs ── */}
          <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-5">
            <StatCard label="Status" value={<span className="text-base"><Badge value={result.status} /></span>} hint={result.solver.split(" (")[0]} />
            <StatCard label="Distance" value={`${result.total_distance_km} km`} hint={`incl. ${result.return_leg_km} km return leg`} tone="lime" />
            <StatCard label="Est. fuel" value={`${result.estimated_fuel_litres} L`} hint={`≈ ₹${result.estimated_fuel_cost} total · ${truck?.fuel_type}`} tone="warn" />
            <StatCard label="vs baseline" value={result.savings_percent != null ? `${result.savings_percent}%` : "—"} hint={result.baseline ? `baseline ${result.baseline.distance_km} km` : "no baseline"} tone="good" />
            <StatCard label="Load" value={`${Math.round(totalDemand)} L`} hint={`of ${truck?.capacity_litres}L capacity`} tone={totalDemand > (truck?.capacity_litres ?? 0) ? "bad" : "default"} />
          </div>

          {/* ── map + stops ── */}
          <div className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
            <CityMap
              bins={bins.data?.items ?? []}
              depot={depots.data.find((d) => d.id === result.depot_id) ?? null}
              stops={result.stops}
              selectedBinId={selectedBin}
              onSelectBin={setSelectedBin}
            />

            <Card title="Ordered stops" subtitle={`${result.stops.length} stops · ${result.unserved_bin_ids.length} unserved`}>
              {result.stops.length > 0 ? (
                <ol className="space-y-2">
                  <li className="flex items-center gap-3 rounded-xl bg-panel2 px-3 py-2 text-xs">
                    <span className="text-peri">▣</span> Depart {result.depot_id}
                  </li>
                  {result.stops.map((s) => (
                    <li
                      key={s.bin_id}
                      className={`flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2 transition-colors ${
                        selectedBin === s.bin_id ? "border-lime/40 bg-lime/5" : "border-edge/50 bg-panel2/50 hover:border-peri/30"
                      }`}
                      onClick={() => setSelectedBin(s.bin_id)}
                    >
                      <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-lime text-[11px] font-bold text-white">
                        {s.sequence}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium text-ink">{s.name.replace(" (Demo)", "")}</p>
                        <p className="text-[11px] text-dim">{s.bin_id} · {s.zone} · {Math.round(s.demand_litres)}L</p>
                      </div>
                      <span className="shrink-0 text-[11px] tabular-nums text-dim">+{s.distance_from_previous_km} km</span>
                    </li>
                  ))}
                  <li className="flex items-center gap-3 rounded-xl bg-panel2 px-3 py-2 text-xs">
                    <span className="text-peri">▣</span> Return to depot <span className="ml-auto text-dim">+{result.return_leg_km} km</span>
                  </li>
                </ol>
              ) : (
                <EmptyState title="No stops — no bins needed collection" hint="Run a simulation tick to fill the bins" />
              )}
              {result.unserved_bin_ids.length > 0 && (
                <p className="mt-3 rounded-lg bg-warning/10 px-3 py-2 text-[11px] text-warning">
                  Unserved (capacity): {result.unserved_bin_ids.join(", ")}
                </p>
              )}
            </Card>
          </div>

          {/* ── explainability ── */}
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card title="Why these bins were selected" subtitle="Explainable decisions from the Bin + Prediction agents">
              <ul className="space-y-3">
                {result.selected_bins.map((b) => (
                  <li key={b.bin_id} className="rounded-xl border border-edge/50 bg-panel2/40 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-ink">
                        {b.bin_id} · {b.name.replace(" (Demo)", "")}
                      </p>
                      <div className="flex gap-1.5">
                        <Badge value={b.status} />
                        {b.predicted_fill_at_horizon != null && (
                          <span className="rounded-full bg-peri/10 px-2 py-0.5 text-[10px] font-semibold text-peri">
                            →{Math.round(b.predicted_fill_at_horizon)}% @{result.planning_horizon_hours}h
                          </span>
                        )}
                      </div>
                    </div>
                    <ul className="mt-1.5 space-y-0.5">
                      {b.reasons.map((r, i) => (
                        <li key={i} className="text-[11px] text-dim">• {r}</li>
                      ))}
                    </ul>
                  </li>
                ))}
                {result.selected_bins.length === 0 && <EmptyState title="Nothing selected" />}
              </ul>
            </Card>

            <div className="space-y-4">
              <Card title="Agent activity in this run" subtitle="Every decision is traceable">
                <ul className="space-y-2">
                  {result.agents.map((a) => (
                    <li key={a.agent_name} className="flex items-center gap-3 rounded-xl border border-edge/50 bg-panel2/40 px-3 py-2">
                      <Badge value={a.status} />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-ink">{a.agent_name}</p>
                        <p className="truncate text-[11px] text-dim" title={a.summary}>{a.summary}</p>
                      </div>
                      <span className="shrink-0 text-[11px] tabular-nums text-dim">{a.duration_ms}ms</span>
                    </li>
                  ))}
                </ul>
              </Card>

              {result.recycling_summary && (
                <Card title="Recycling insights" subtitle={result.recycling_summary.note}>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(result.recycling_summary.distribution).map(([cat, n]) => (
                      <span key={cat} className="rounded-full border border-edge bg-panel2 px-3 py-1 text-xs text-ink">
                        {cat} <b className="text-lime">×{n}</b>
                      </span>
                    ))}
                  </div>
                  {result.recycling_summary.diversion_estimate_percent != null && (
                    <p className="mt-3 text-xs text-dim">
                      Diversion estimate: <b className="text-lime">{result.recycling_summary.diversion_estimate_percent}%</b> of collected volume is recyclable/compostable.
                    </p>
                  )}
                  <ul className="mt-3 space-y-1.5">
                    {result.recycling_summary.recommendations.map((r) => (
                      <li key={r.category} className="text-[11px] text-dim">
                        <b className="text-ink">{r.category}:</b> {r.recommendation}
                        {r.caution && <span className="ml-1 text-warning">⚠ {r.caution}</span>}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {result.warnings.length > 0 && (
                <Card title="Warnings" subtitle="Transparent limitations of this run">
                  <ul className="space-y-1.5">
                    {result.warnings.map((w, i) => (
                      <li key={i} className="rounded-lg bg-warning/5 px-3 py-2 text-[11px] text-dim">⚠ {w}</li>
                    ))}
                  </ul>
                </Card>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}

function AgentChip({ name, active }: { name: string; active: boolean }) {
  return (
    <span className={`rounded-full border px-3 py-1.5 text-xs ${active ? "border-lime/40 bg-lime/10 text-lime" : "border-edge text-dim"}`}>
      ⬡ {name}
    </span>
  );
}

function Arrow() {
  return <span className="text-dim/50">→</span>;
}
