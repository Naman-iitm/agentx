import { useMemo, useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks";
import CityMap from "../components/CityMap";
import { Badge, Card, EmptyState, ErrorState, FillBar, PageHeader, Select, Spinner } from "../components/ui";
import type { Bin } from "../types";

export default function MapPage() {
  const bins = useApi(() => api.bins({ limit: "200" }), []);
  const depots = useApi(() => api.depots(), []);
  const runs = useApi(() => api.runs(1), []);
  const [zone, setZone] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [useRoute, setUseRoute] = useState(true);

  const zones = useMemo(
    () => [...new Set((bins.data?.items ?? []).map((b) => b.zone))].sort(),
    [bins.data]
  );

  const filtered = useMemo(
    () =>
      (bins.data?.items ?? []).filter(
        (b) => (!zone || b.zone === zone) && (!status || b.status === status)
      ),
    [bins.data, zone, status]
  );

  const latestRun = runs.data?.items?.[0];
  const routeDetail = useApi(
    async () => (latestRun && useRoute ? await api.run(latestRun.run_id) : null),
    [latestRun?.run_id, useRoute]
  );

  const selectedBin: Bin | undefined = useMemo(
    () => (bins.data?.items ?? []).find((b) => b.id === selected),
    [bins.data, selected]
  );

  if (bins.status === "loading") return <Spinner label="Loading map…" />;
  if (bins.status === "error" || !bins.data)
    return <ErrorState message={bins.error} onRetry={bins.reload} />;

  return (
    <>
      <PageHeader
        title="Live Bin Map"
        subtitle="Schematic city view — markers show fill level, colour shows status"
        actions={
          <>
            <Select
              value={zone}
              onChange={setZone}
              options={[{ value: "", label: "All zones" }, ...zones.map((z) => ({ value: z, label: z }))]}
            />
            <Select
              value={status}
              onChange={setStatus}
              options={[
                { value: "", label: "All statuses" },
                { value: "CRITICAL", label: "Critical" },
                { value: "WARNING", label: "Warning" },
                { value: "NORMAL", label: "Normal" },
              ]}
            />
            {latestRun && (
              <button
                onClick={() => setUseRoute((v) => !v)}
                className={`rounded-full border px-3 py-2 text-xs font-semibold transition-colors ${
                  useRoute ? "border-lime/40 bg-lime/15 text-lime" : "border-edge bg-panel2 text-dim"
                }`}
              >
                {useRoute ? "● Route shown" : "○ Show latest route"}
              </button>
            )}
          </>
        }
      />

      <CityMap
        bins={filtered}
        depot={depots.data?.[0] ?? null}
        stops={useRoute ? (routeDetail.data?.stops ?? []) : []}
        selectedBinId={selected}
        onSelectBin={setSelected}
      />

      {selectedBin && (
        <Card className="mt-4" title={selectedBin.name} subtitle={`${selectedBin.id} · ${selectedBin.zone} · ${selectedBin.bin_type}`}>
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs text-dim">Fill level</p>
              <p className="mt-1 text-2xl font-bold tabular-nums text-ink">{selectedBin.fill_percent}%</p>
              <div className="mt-2">
                <FillBar percent={selectedBin.fill_percent ?? 0} status={selectedBin.status} />
              </div>
            </div>
            <div>
              <p className="text-xs text-dim">Status</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedBin.status && <Badge value={selectedBin.status} />}
                {selectedBin.is_stale && <Badge value="STALE" />}
              </div>
              <p className="mt-3 text-xs text-dim">
                Battery: {selectedBin.battery_percent != null ? `${selectedBin.battery_percent}%` : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs text-dim">Last reading</p>
              <p className="mt-1 text-sm text-ink">
                {selectedBin.measured_at ? new Date(selectedBin.measured_at).toLocaleString() : "no data"}
              </p>
              <p className="mt-1 text-xs text-dim/70">source: {selectedBin.reading_source ?? "—"}</p>
            </div>
          </div>
        </Card>
      )}

      {useRoute && routeDetail.data && (
        <Card
          className="mt-4"
          title="Latest collection route"
          subtitle={`${routeDetail.data.solver} · ${routeDetail.data.total_distance_km} km · ₹${routeDetail.data.estimated_fuel_cost} est. fuel`}
        >
          {routeDetail.data.stops.length > 0 ? (
            <ol className="flex flex-wrap items-center gap-2 text-sm">
              <li className="rounded-lg bg-panel2 px-3 py-1.5 text-xs text-peri">Depot</li>
              {routeDetail.data.stops.map((s) => (
                <li key={s.bin_id} className="flex items-center gap-2">
                  <span className="text-dim">→</span>
                  <span className="rounded-lg bg-panel2 px-3 py-1.5 text-xs text-ink">
                    <b className="text-lime">{s.sequence}.</b> {s.bin_id}{" "}
                    <span className="text-dim">+{s.distance_from_previous_km}km</span>
                  </span>
                </li>
              ))}
              <span className="text-dim">→</span>
              <li className="rounded-lg bg-panel2 px-3 py-1.5 text-xs text-peri">Depot</li>
            </ol>
          ) : (
            <EmptyState title="No stops in the latest run" />
          )}
        </Card>
      )}
    </>
  );
}
