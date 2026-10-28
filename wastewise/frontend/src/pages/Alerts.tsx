import { useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks";
import { Button, Card, EmptyState, ErrorState, PageHeader, Select, SeverityBadge, Spinner } from "../components/ui";

const TYPE_LABELS: Record<string, string> = {
  OVERFLOW_RISK: "Overflow risk",
  SENSOR_STALE: "Stale sensor",
  BATTERY_LOW: "Low battery",
  ROUTE_INFEASIBLE: "Route infeasible",
  FORECAST_ANOMALY: "Forecast anomaly",
};

export default function Alerts() {
  const [status, setStatus] = useState("OPEN");
  const [severity, setSeverity] = useState("");
  const alerts = useApi(
    () => api.alerts({ ...(status ? { status } : {}), ...(severity ? { severity } : {}), limit: "100" }),
    [status, severity]
  );
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const act = async (id: number, action: "acknowledge" | "resolve") => {
    setBusyId(id);
    setError("");
    try {
      if (action === "acknowledge") await api.acknowledgeAlert(id);
      else await api.resolveAlert(id);
      await alerts.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Alerts"
        subtitle="Overfill risk, stale sensors, low batteries — with validated state transitions"
        actions={
          <>
            <Select
              value={status}
              onChange={setStatus}
              options={[
                { value: "", label: "Any status" },
                { value: "OPEN", label: "Open" },
                { value: "ACKNOWLEDGED", label: "Acknowledged" },
                { value: "RESOLVED", label: "Resolved" },
              ]}
            />
            <Select
              value={severity}
              onChange={setSeverity}
              options={[
                { value: "", label: "Any severity" },
                { value: "CRITICAL", label: "Critical" },
                { value: "HIGH", label: "High" },
                { value: "MEDIUM", label: "Medium" },
                { value: "LOW", label: "Low" },
              ]}
            />
          </>
        }
      />

      {error && (
        <p className="mb-4 rounded-lg bg-critical/10 px-4 py-2.5 text-xs text-critical">{error}</p>
      )}

      <Card>
        {alerts.status === "loading" ? (
          <Spinner />
        ) : alerts.status === "error" ? (
          <ErrorState message={alerts.error} onRetry={alerts.reload} />
        ) : alerts.data && alerts.data.items.length > 0 ? (
          <ul className="divide-y divide-edge/40">
            {alerts.data.items.map((a) => (
              <li key={a.id} className="flex flex-wrap items-start gap-3 py-4">
                <span
                  className={`mt-1.5 size-2.5 shrink-0 rounded-full ${
                    a.severity === "CRITICAL" ? "bg-critical" : a.severity === "HIGH" ? "bg-warning" : "bg-peri"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-ink">{a.title}</p>
                    <SeverityBadge severity={a.severity} />
                    <span className="rounded-full border border-edge px-2 py-0.5 text-[10px] font-semibold text-dim">
                      {TYPE_LABELS[a.type] ?? a.type}
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-dim">{a.message}</p>
                  <p className="mt-1.5 text-[11px] text-dim/60">
                    {new Date(a.created_at).toLocaleString()}
                    {a.bin_id ? ` · ${a.bin_id}` : ""}
                    {a.acknowledged_at && ` · ack’d ${new Date(a.acknowledged_at).toLocaleTimeString()}`}
                    {a.resolved_at && ` · resolved ${new Date(a.resolved_at).toLocaleTimeString()}`}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  {a.status === "OPEN" && (
                    <Button variant="secondary" className="!px-3 !py-1.5 text-xs" onClick={() => act(a.id, "acknowledge")} disabled={busyId === a.id}>
                      Acknowledge
                    </Button>
                  )}
                  {a.status !== "RESOLVED" && (
                    <Button variant="primary" className="!px-3 !py-1.5 text-xs" onClick={() => act(a.id, "resolve")} disabled={busyId === a.id}>
                      Resolve
                    </Button>
                  )}
                  {a.status === "RESOLVED" && (
                    <span className="rounded-full bg-normal/10 px-3 py-1.5 text-[11px] font-semibold text-normal">RESOLVED</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No alerts match the filters" hint="All clear — or adjust the filters" />
        )}
      </Card>
    </>
  );
}
