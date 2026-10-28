import { useEffect, useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks";
import { Button, Card, DemoTag, ErrorState, PageHeader, Spinner } from "../components/ui";
import type { Settings as SettingsT } from "../types";

export default function SettingsPage() {
  const settings = useApi(() => api.settings(), []);
  const [form, setForm] = useState<SettingsT | null>(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    if (settings.data && !form) setForm(settings.data);
  }, [settings.data, form]);

  const set = (key: keyof SettingsT, value: number) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  const save = async () => {
    if (!form) return;
    setSaving(true);
    setFeedback(null);
    try {
      await api.patchSettings({
        warning_threshold: form.warning_threshold,
        critical_threshold: form.critical_threshold,
        collection_threshold: form.collection_threshold,
        stale_after_hours: form.stale_after_hours,
        fuel_price_per_litre: form.fuel_price_per_litre,
        planning_horizon_hours: form.planning_horizon_hours,
        road_distance_factor: form.road_distance_factor,
      });
      setFeedback({ ok: true, text: "Settings saved — an audit event was recorded." });
      await settings.reload();
      setForm(null); // re-sync from server
    } catch (e) {
      setFeedback({ ok: false, text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const resetDemo = async () => {
    setSaving(true);
    try {
      await api.resetDemo();
      setFeedback({ ok: true, text: "Demo telemetry regenerated." });
    } catch (e) {
      setFeedback({ ok: false, text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  if (settings.status === "loading") return <Spinner label="Loading settings…" />;
  if (settings.status === "error" || !settings.data)
    return <ErrorState message={settings.error} onRetry={settings.reload} />;

  const s = form ?? settings.data;

  const numberField = (
    label: string,
    key: keyof SettingsT,
    props: { min?: number; max?: number; step?: number; hint?: string }
  ) => (
    <label className="block">
      <span className="text-xs font-medium text-dim">{label}</span>
      <input
        type="number"
        value={String(s[key] ?? "")}
        min={props.min}
        max={props.max}
        step={props.step ?? 1}
        onChange={(e) => set(key, Number(e.target.value))}
        className="mt-1 w-full rounded-lg border border-edge bg-panel2 px-3 py-2 text-sm tabular-nums text-ink outline-none focus:border-peri/60"
      />
      {props.hint && <span className="mt-1 block text-[11px] text-dim/60">{props.hint}</span>}
    </label>
  );

  return (
    <>
      <PageHeader
        title="Settings & Data Sources"
        subtitle="Operational thresholds and assumptions — changes are validated and audited"
        actions={<DemoTag>{settings.data.demo_mode ? "demo mode on" : "demo mode off"}</DemoTag>}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Thresholds" subtitle="Used by the Bin Agent for status and candidate selection">
          <div className="grid gap-4 sm:grid-cols-3">
            {numberField("Warning %", "warning_threshold", { min: 0, max: 100 })}
            {numberField("Critical %", "critical_threshold", { min: 0, max: 100 })}
            {numberField("Collection %", "collection_threshold", { min: 0, max: 100, hint: "bins ≥ this become candidates" })}
            {numberField("Stale after (h)", "stale_after_hours", { min: 1, max: 168, step: 0.5 })}
            {numberField("Horizon (h)", "planning_horizon_hours", { min: 1, max: 72 })}
            {numberField("Road factor", "road_distance_factor", { min: 1, max: 3, step: 0.05, hint: "haversine × factor ≈ road km" })}
          </div>
          <p className="mt-4 rounded-lg bg-panel2 px-3 py-2 text-[11px] leading-relaxed text-dim">
            Rule: <b className="text-ink">0 ≤ warning &lt; critical ≤ 100</b> and warning ≤ collection ≤ 100. Invalid values are rejected server-side.
          </p>
        </Card>

        <div className="space-y-4">
          <Card title="Fuel assumptions" subtitle="Demo values — clearly labelled in every estimate">
            <div className="grid gap-4 sm:grid-cols-2">
              {numberField("Fuel price (₹/L)", "fuel_price_per_litre", { min: 1, max: 1000, step: 0.5 })}
              {numberField("Default consumption (L/100km)", "default_consumption_l_per_100km", { min: 1, max: 100, step: 0.5 })}
            </div>
            <p className="mt-4 text-[11px] leading-relaxed text-dim/70">
              Routing provider: <b className="text-ink">{settings.data.routing_provider}</b> — straight-line distances × road factor, a documented approximation (no live traffic API).
            </p>
          </Card>

          <Card title="Demo controls" subtitle="Simulation endpoints (DEMO_MODE only)">
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={resetDemo} disabled={saving}>
                ↺ Regenerate demo telemetry
              </Button>
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-dim/70">
              Regenerates 48h of simulated history for every bin and re-evaluates alerts — handy before an exhibition demo loop. Never available in production.
            </p>
          </Card>

          <Card title="Save">
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={save} disabled={saving || !form}>
                {saving ? "Saving…" : "Save settings"}
              </Button>
              <span className="text-[11px] text-dim">
                Last updated {new Date(settings.data.updated_at).toLocaleString()}
              </span>
            </div>
            {feedback && (
              <p className={`mt-3 rounded-lg px-3 py-2 text-xs ${feedback.ok ? "bg-normal/10 text-normal" : "bg-critical/10 text-critical"}`}>
                {feedback.text}
              </p>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
