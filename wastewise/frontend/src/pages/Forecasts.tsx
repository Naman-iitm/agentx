import { useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks";
import { ForecastChart } from "../components/charts";
import { Card, DemoTag, EmptyState, ErrorState, PageHeader, Select, Spinner } from "../components/ui";

export default function Forecasts() {
  const bins = useApi(() => api.bins({ limit: "200" }), []);
  const [binId, setBinId] = useState("");
  const [horizon, setHorizon] = useState("24");

  const effectiveBin = binId || bins.data?.items?.[0]?.id || "";
  const forecast = useApi(
    () => (effectiveBin ? api.forecast(effectiveBin, Number(horizon)) : Promise.resolve(null)),
    [effectiveBin, horizon]
  );
  const readings = useApi(
    () => (effectiveBin ? api.binReadings(effectiveBin, 72) : Promise.resolve(null)),
    [effectiveBin]
  );

  if (bins.status === "loading") return <Spinner label="Loading bins…" />;
  if (!bins.data) return <ErrorState message={bins.error} />;
  if (bins.data.items.length === 0) return <EmptyState title="No bins available" />;

  const f = forecast.data;
  const history = (readings.data?.items ?? [])
    .slice()
    .reverse()
    .map((r) => ({ t: r.measured_at, v: r.fill_percent }));

  return (
    <>
      <PageHeader
        title="Waste Forecasts"
        subtitle="Predicted fill levels from the transparent rolling-slope baseline — never presented as sensor readings"
        actions={<DemoTag>model estimates</DemoTag>}
      />

      <Card
        title="Configure forecast"
        subtitle={`${f?.method ?? "rolling-slope-v1"} · ${f?.model_version ?? "baseline-1.0"}`}
        right={
          <div className="flex gap-2">
            <Select
              value={effectiveBin}
              onChange={setBinId}
              options={bins.data.items.map((b) => ({
                value: b.id,
                label: `${b.id} · ${b.name.replace(" (Demo)", "")} (${Math.round(b.fill_percent ?? 0)}%)`,
              }))}
            />
            <Select
              value={horizon}
              onChange={setHorizon}
              options={[6, 12, 24, 48, 72].map((h) => ({ value: String(h), label: `${h}h horizon` }))}
            />
          </div>
        }
      >
        {forecast.status === "loading" || readings.status === "loading" ? (
          <Spinner label="Computing forecast…" />
        ) : forecast.status === "error" ? (
          <ErrorState message={forecast.error} onRetry={forecast.reload} />
        ) : !f ? (
          <EmptyState title="Select a bin" />
        ) : f.status === "insufficient_history" ? (
          <div className="rounded-xl border border-warning/30 bg-warning/5 p-6 text-center">
            <p className="text-sm font-semibold text-warning">Insufficient history</p>
            <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-dim">{f.note}</p>
            <ul className="mt-3 space-y-1">
              {f.warnings.map((w, i) => (
                <li key={i} className="text-[11px] text-dim">• {w}</li>
              ))}
            </ul>
          </div>
        ) : (
          <>
            <ForecastChart
              history={history}
              forecast={f.points.map((p) => ({ t: p.target_at, v: p.predicted_fill_percent, lo: p.lower_bound, hi: p.upper_bound }))}
            />
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px] text-dim">
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-0.5 w-5 bg-peri" /> measured history (72h)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-0.5 w-5 border-t-2 border-dashed border-lime" /> prediction
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-5 rounded bg-lime/15" /> 95% uncertainty band
              </span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-panel2 px-4 py-3">
                <p className="text-[10px] uppercase tracking-wider text-dim">Predicted at {f.horizon_hours}h</p>
                <p className="mt-1 text-xl font-bold tabular-nums text-lime">
                  {f.points[f.points.length - 1]?.predicted_fill_percent}%
                </p>
              </div>
              <div className="rounded-xl bg-panel2 px-4 py-3">
                <p className="text-[10px] uppercase tracking-wider text-dim">Range at horizon</p>
                <p className="mt-1 text-xl font-bold tabular-nums text-ink">
                  {f.points[f.points.length - 1]?.lower_bound}–{f.points[f.points.length - 1]?.upper_bound}%
                </p>
              </div>
              <div className="rounded-xl bg-panel2 px-4 py-3">
                <p className="text-[10px] uppercase tracking-wider text-dim">Generated</p>
                <p className="mt-1 text-sm font-semibold text-ink">{new Date(f.generated_at).toLocaleString()}</p>
              </div>
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-dim/70">ℹ {f.note}</p>
            {f.warnings.length > 0 && (
              <ul className="mt-2 space-y-1">
                {f.warnings.map((w, i) => (
                  <li key={i} className="text-[11px] text-warning">⚠ {w}</li>
                ))}
              </ul>
            )}
          </>
        )}
      </Card>
    </>
  );
}
