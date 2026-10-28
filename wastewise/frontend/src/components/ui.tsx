import type { ReactNode } from "react";

// ─── layout primitives ───────────────────────────────────────────────────────

export function Card({
  title,
  subtitle,
  right,
  children,
  className = "",
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-edge bg-panel/80 shadow-lg shadow-black/20 ${className}`}
    >
      {(title || right) && (
        <header className="flex items-start justify-between gap-3 border-b border-edge/60 px-5 py-4">
          <div>
            {title && <h2 className="text-sm font-semibold tracking-wide text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-dim">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-dim">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2">{actions}</div>
    </div>
  );
}

// ─── status indicators ───────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  NORMAL: "bg-normal/15 text-normal border-normal/30",
  WARNING: "bg-warning/15 text-warning border-warning/30",
  CRITICAL: "bg-critical/15 text-critical border-critical/30",
  STALE: "bg-stale/15 text-stale border-stale/30",
  OPEN: "bg-critical/15 text-critical border-critical/30",
  ACKNOWLEDGED: "bg-warning/15 text-warning border-warning/30",
  RESOLVED: "bg-normal/15 text-normal border-normal/30",
  FEASIBLE: "bg-normal/15 text-normal border-normal/30",
  PARTIAL: "bg-warning/15 text-warning border-warning/30",
  INFEASIBLE: "bg-critical/15 text-critical border-critical/30",
  FAILED: "bg-critical/15 text-critical border-critical/30",
  success: "bg-normal/15 text-normal border-normal/30",
  partial: "bg-warning/15 text-warning border-warning/30",
  skipped: "bg-dim/15 text-dim border-dim/30",
  failed: "bg-critical/15 text-critical border-critical/30",
  CRITICAL_SEV: "bg-critical/20 text-critical border-critical/40",
  HIGH: "bg-warning/15 text-warning border-warning/30",
  MEDIUM: "bg-peri/15 text-peri border-peri/30",
  LOW: "bg-dim/15 text-dim border-dim/30",
};

export function Badge({ value, className = "" }: { value: string; className?: string }) {
  const style = STATUS_STYLES[value] ?? "bg-dim/15 text-dim border-dim/30";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${style} ${className}`}
    >
      {value}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    CRITICAL: "bg-critical/20 text-critical border-critical/40",
    HIGH: "bg-warning/15 text-warning border-warning/30",
    MEDIUM: "bg-peri/15 text-peri border-peri/30",
    LOW: "bg-dim/15 text-dim border-dim/30",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-bold tracking-wide ${map[severity] ?? map.LOW}`}
    >
      {severity}
    </span>
  );
}

// ─── data display ────────────────────────────────────────────────────────────

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "good" | "warn" | "bad" | "lime";
}) {
  const tones: Record<string, string> = {
    default: "text-ink",
    good: "text-normal",
    warn: "text-warning",
    bad: "text-critical",
    lime: "text-lime",
  };
  return (
    <div className="rounded-2xl border border-edge bg-panel/80 px-5 py-4 shadow-lg shadow-black/20">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-dim">{label}</p>
      <p className={`mt-1.5 text-2xl font-bold tabular-nums ${tones[tone]}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-dim">{hint}</p>}
    </div>
  );
}

export function FillBar({ percent, status }: { percent: number; status?: string | null }) {
  const color =
    status === "CRITICAL"
      ? "bg-critical"
      : status === "WARNING"
        ? "bg-warning"
        : "bg-normal";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-edge/60">
      <div
        className={`h-full rounded-full ${color} transition-all`}
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}

// ─── interaction ─────────────────────────────────────────────────────────────

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  className = "",
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  disabled?: boolean;
  className?: string;
  type?: "button" | "submit";
}) {
  const styles = {
    primary: "bg-lime text-white hover:bg-lime/85 font-semibold",
    secondary: "border border-edge bg-panel2 text-ink hover:border-peri/50",
    ghost: "text-dim hover:text-ink",
    danger: "border border-critical/40 bg-critical/10 text-critical hover:bg-critical/20",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Select({
  value,
  onChange,
  options,
  className = "",
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  className?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`rounded-lg border border-edge bg-panel2 px-3 py-2 text-sm text-ink outline-none focus:border-peri/60 ${className}`}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

// ─── states ──────────────────────────────────────────────────────────────────

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-dim">
      <span className="size-4 animate-spin rounded-full border-2 border-edge border-t-peri" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-edge py-12 text-center">
      <p className="text-sm font-medium text-dim">{title}</p>
      {hint && <p className="mt-1 text-xs text-dim/70">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-critical/30 bg-critical/5 py-10 text-center">
      <p className="text-sm font-semibold text-critical">Something went wrong</p>
      <p className="mx-auto mt-1 max-w-md text-xs text-dim">{message}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function DemoTag({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-warning">
      <span className="pulse-dot inline-block size-1.5 rounded-full bg-warning" />
      {children}
    </span>
  );
}
