import { Fragment, useMemo, useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks";
import { Sparkline } from "../components/charts";
import { Badge, Button, Card, EmptyState, ErrorState, FillBar, PageHeader, Select, Spinner } from "../components/ui";

export default function Bins() {
  const [search, setSearch] = useState("");
  const [zone, setZone] = useState("");
  const [status, setStatus] = useState("");
  const bins = useApi(() => api.bins({ limit: "200" }), []);
  const [expanded, setExpanded] = useState<string | null>(null);
  const readings = useApi(
    () => (expanded ? api.binReadings(expanded, 48) : Promise.resolve(null)),
    [expanded]
  );
  const [addingReading, setAddingReading] = useState<string | null>(null);

  const zones = useMemo(
    () => [...new Set((bins.data?.items ?? []).map((b) => b.zone))].sort(),
    [bins.data]
  );

  const filtered = useMemo(
    () =>
      (bins.data?.items ?? []).filter(
        (b) =>
          (!zone || b.zone === zone) &&
          (!status || b.status === status) &&
          (!search ||
            b.name.toLowerCase().includes(search.toLowerCase()) ||
            b.id.toLowerCase().includes(search.toLowerCase()))
      ),
    [bins.data, zone, status, search]
  );

  const sendReading = async (binId: string, fill: number) => {
    setAddingReading(binId);
    try {
      await api.postReading(binId, fill);
      await bins.reload();
      if (expanded === binId) await readings.reload();
    } finally {
      setAddingReading(null);
    }
  };

  if (bins.status === "loading") return <Spinner label="Loading bins…" />;
  if (bins.status === "error" || !bins.data)
    return <ErrorState message={bins.error} onRetry={bins.reload} />;

  return (
    <>
      <PageHeader
        title="Bins & Sensors"
        subtitle={`${bins.data.total} active bins · demo telemetry, clearly labelled`}
        actions={
          <>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name or ID…"
              className="w-44 rounded-lg border border-edge bg-panel2 px-3 py-2 text-sm text-ink outline-none placeholder:text-dim/50 focus:border-peri/60"
            />
            <Select value={zone} onChange={setZone} options={[{ value: "", label: "All zones" }, ...zones.map((z) => ({ value: z, label: z }))]} />
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
          </>
        }
      />

      <Card>
        {filtered.length === 0 ? (
          <EmptyState title="No bins match the filters" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-edge/60 text-left text-[11px] uppercase tracking-wider text-dim">
                  <th className="pb-3 pr-4 font-semibold">Bin</th>
                  <th className="pb-3 pr-4 font-semibold">Zone</th>
                  <th className="pb-3 pr-4 font-semibold">Fill level</th>
                  <th className="pb-3 pr-4 font-semibold">Status</th>
                  <th className="pb-3 pr-4 font-semibold">Battery</th>
                  <th className="pb-3 pr-4 font-semibold">Trend (48h)</th>
                  <th className="pb-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-edge/40">
                {filtered.map((b) => (
                  <Fragment key={b.id}>
                    <tr className="hover:bg-panel2/40">
                      <td className="py-3 pr-4">
                        <button className="text-left" onClick={() => setExpanded(expanded === b.id ? null : b.id)}>
                          <p className="font-medium text-ink">{b.name.replace(" (Demo)", "")}</p>
                          <p className="text-xs text-dim">{b.id} · {b.bin_type}</p>
                        </button>
                      </td>
                      <td className="py-3 pr-4 text-dim">{b.zone}</td>
                      <td className="py-3 pr-4">
                        <div className="w-36">
                          <div className="mb-1 flex justify-between text-xs">
                            <span className="font-bold tabular-nums text-ink">{b.fill_percent}%</span>
                            <span className="text-dim/60">{b.capacity_litres}L</span>
                          </div>
                          <FillBar percent={b.fill_percent ?? 0} status={b.status} />
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex flex-wrap gap-1.5">
                          {b.status && <Badge value={b.status} />}
                          {b.is_stale && <Badge value="STALE" />}
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`tabular-nums text-xs ${b.battery_percent != null && b.battery_percent < 20 ? "font-bold text-critical" : "text-dim"}`}>
                          {b.battery_percent != null ? `${Math.round(b.battery_percent)}%` : "—"}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        {b.is_stale ? (
                          <span className="text-xs text-stale">stale sensor</span>
                        ) : (
                          <Sparkline points={expanded === b.id ? (readings.data?.items ?? []).slice().reverse().map((r) => r.fill_percent) : []} />
                        )}
                      </td>
                      <td className="py-3">
                        <div className="flex gap-1.5">
                          <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => sendReading(b.id, Math.min(100, (b.fill_percent ?? 0) + 5))} disabled={addingReading === b.id}>
                            +5%
                          </Button>
                          <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => sendReading(b.id, 20)} disabled={addingReading === b.id}>
                            emptied
                          </Button>
                        </div>
                      </td>
                    </tr>
                    {expanded === b.id && (
                      <tr className="bg-panel2/30">
                        <td colSpan={7} className="px-4 py-4">
                          {readings.status === "loading" ? (
                            <Spinner label="Loading readings…" />
                          ) : readings.data ? (
                            <div>
                              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-dim">
                                Recent readings (newest first, source: {readings.data.items[0]?.source ?? "—"})
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {readings.data.items.slice(0, 24).map((r) => (
                                  <span
                                    key={r.id}
                                    title={`${new Date(r.measured_at).toLocaleString()} · ${r.source}${r.quality_flag !== "GOOD" ? ` · ${r.quality_flag}` : ""}`}
                                    className={`rounded-md px-2 py-1 text-[11px] tabular-nums ${
                                      r.quality_flag === "STALE"
                                        ? "bg-stale/15 text-stale"
                                        : r.fill_percent >= 90
                                          ? "bg-critical/15 text-critical"
                                          : r.fill_percent >= 70
                                            ? "bg-warning/15 text-warning"
                                            : "bg-normal/10 text-normal"
                                    }`}
                                  >
                                    {Math.round(r.fill_percent)}%
                                  </span>
                                ))}
                              </div>
                              <p className="mt-3 text-[11px] text-dim/60">
                                Readings are demo telemetry (source: simulator). Status is computed server-side by the Bin Agent.
                              </p>
                            </div>
                          ) : (
                            <EmptyState title="No readings" />
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
