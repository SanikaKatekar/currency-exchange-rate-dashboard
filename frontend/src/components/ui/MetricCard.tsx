/**
 * KPI card used in the dashboard summary row.
 */
import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  icon: ReactNode;
  accent?: "neutral" | "positive" | "negative";
}

/** Highlight card for a single headline FX metric. */
export function MetricCard({ label, value, hint, icon, accent = "neutral" }: MetricCardProps) {
  const valueClass =
    accent === "positive"
      ? "positive"
      : accent === "negative"
        ? "negative"
        : "text-[var(--text-primary)]";

  return (
    <article className="glass-panel gradient-border rounded-3xl p-5">
      <div className="mb-8 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--text-secondary)]">{label}</p>
          {hint && <p className="mt-1 text-xs text-[var(--text-muted)]">{hint}</p>}
        </div>
        <div className="rounded-2xl bg-[var(--accent-glow)] p-3 text-[var(--accent)]">{icon}</div>
      </div>
      <p className={`font-display text-4xl font-semibold tracking-tight ${valueClass}`}>{value}</p>
    </article>
  );
}
