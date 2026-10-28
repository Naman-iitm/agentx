import { useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks";
import { DonutChart } from "../components/charts";
import { Button, Card, EmptyState, ErrorState, PageHeader, Select, Spinner, StatCard } from "../components/ui";

const COLORS = ["#059669", "#0284c7", "#65a30d", "#d97706", "#dc2626", "#7c3aed", "#db2777", "#0369a1", "#64748b"];

export default function Recycling() {
  const summary = useApi(() => api.recyclingSummary(), []);
  const classifications = useApi(() => api.classifications(30), []);
  const bins = useApi(() => api.bins({ limit: "200" }), []);

  const [binId, setBinId] = useState("");
  const [category, setCategory] = useState("PLASTIC");
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);

  const CATEGORIES = ["ORGANIC", "PAPER", "PLASTIC", "METAL", "GLASS", "E_WASTE", "HAZARDOUS", "MIXED", "UNKNOWN"];

  const submit = async () => {
    setSaving(true);
    setFeedback(null);
    try {
      const result = await api.classify({
        bin_id: binId || null,
        category,
        source: "operator",
      });
      setFeedback({
        ok: true,
        text: `Saved: ${result.category}${result.bin_id ? ` for ${result.bin_id}` : ""}. ${result.recommendation}${result.caution ? ` ⚠ ${result.caution}` : ""}`,
      });
      await Promise.all([summary.reload(), classifications.reload()]);
    } catch (e) {
      setFeedback({ ok: false, text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  if (summary.status === "loading") return <Spinner label="Loading recycling insights…" />;
  if (summary.status === "error" || !summary.data)
    return <ErrorState message={summary.error} onRetry={summary.reload} />;

  const s = summary.data;

  return (
    <>
      <PageHeader
        title="AI & Sustainability Insights"
        subtitle="Waste categories, handling recommendations and review queue — operator-confirmed in the MVP"
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Classifications" value={s.total_classifications} />
        <StatCard label="Categories" value={s.distribution.length} tone="lime" />
        <StatCard label="Needs review" value={s.review_required_count} tone={s.review_required_count > 0 ? "warn" : "good"} hint="low confidence / hazardous" />
        <StatCard
          label="Top category"
          value={s.distribution[0]?.category ?? "—"}
          hint={s.distribution[0] ? `${s.distribution[0].share_percent}% of records` : ""}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Category distribution" subtitle="All recorded classifications">
          {s.distribution.length > 0 ? (
            <DonutChart
              segments={s.distribution.map((d, i) => ({
                label: d.category,
                value: d.count,
                color: COLORS[i % COLORS.length],
              }))}
              centerValue={String(s.total_classifications)}
              centerLabel="records"
            />
          ) : (
            <EmptyState title="No classifications yet" />
          )}
        </Card>

        <Card title="Handling recommendations" subtitle="Rules-based, versioned (rules-v1)">
          <ul className="space-y-2.5">
            {s.recommendations.map((r) => (
              <li key={r.category} className="rounded-xl border border-edge/50 bg-panel2/40 p-3">
                <p className="text-xs font-bold text-ink">{r.category}</p>
                <p className="mt-0.5 text-[11px] leading-relaxed text-dim">{r.recommendation}</p>
                {r.caution && <p className="mt-1 text-[11px] font-medium text-warning">⚠ {r.caution}</p>}
              </li>
            ))}
            {s.recommendations.length === 0 && <EmptyState title="Nothing to show yet" />}
          </ul>
        </Card>
      </div>

      <Card
        className="mt-4"
        title="Classify waste"
        subtitle="MVP mode: operator selects the category. Vision-model classification is a documented extension."
      >
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-dim">
            Bin (optional)
            <Select
              value={binId}
              onChange={setBinId}
              options={[
                { value: "", label: "— none —" },
                ...(bins.data?.items ?? []).map((b) => ({ value: b.id, label: `${b.id} · ${b.name.replace(" (Demo)", "")}` })),
              ]}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-dim">
            Category
            <Select value={category} onChange={setCategory} options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
          </label>
          <Button onClick={submit} disabled={saving}>
            {saving ? "Saving…" : "Classify"}
          </Button>
        </div>
        {feedback && (
          <p className={`mt-3 rounded-lg px-3 py-2 text-xs ${feedback.ok ? "bg-normal/10 text-normal" : "bg-critical/10 text-critical"}`}>
            {feedback.text}
          </p>
        )}
        <p className="mt-3 text-[11px] text-dim/60">
          Hazardous categories always land in the human-review queue — this system is not a certified hazardous-waste detector.
        </p>
      </Card>

      <Card className="mt-4" title="Recent classifications" subtitle="Newest first">
        {classifications.status === "loading" ? (
          <Spinner />
        ) : classifications.data && classifications.data.items.length > 0 ? (
          <ul className="divide-y divide-edge/40">
            {classifications.data.items.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-3 py-2.5">
                <span className="rounded-lg bg-panel2 px-2.5 py-1 text-xs font-bold text-ink">{c.category}</span>
                <span className="text-xs text-dim">{c.bin_id ?? "unassigned"}</span>
                <span className="text-[11px] text-dim/70">
                  {c.source}
                  {c.confidence != null ? ` · confidence ${(c.confidence * 100).toFixed(0)}%` : ""}
                  {c.model_version ? ` · ${c.model_version}` : ""}
                </span>
                <span className="ml-auto text-[11px] text-dim/70">{new Date(c.created_at).toLocaleString()}</span>
                {c.review_status === "review_required" && (
                  <span className="rounded-full bg-warning/15 px-2 py-0.5 text-[10px] font-bold text-warning">REVIEW REQUIRED</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No classifications recorded" />
        )}
      </Card>
    </>
  );
}
