/**
 * Summary KPI cards for the selected FX period.
 */
import { ArrowDownRight, ArrowUpRight, LineChart, Sigma, TrendingUp } from "lucide-react";
import type { SummaryTotals } from "../types";
import { MetricCard } from "./ui/MetricCard";

/** Format a nullable percentage for display. */
function formatPct(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/** Render the four headline totals returned by the API. */
export function SummaryCards({ totals }: { totals: SummaryTotals }) {
  const changeAccent =
    totals.total_pct_change === null || totals.total_pct_change === 0
      ? "neutral"
      : totals.total_pct_change > 0
        ? "positive"
        : "negative";

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Opening rate"
        value={totals.start_rate.toFixed(4)}
        hint="First published business day in range"
        icon={<TrendingUp size={18} />}
      />
      <MetricCard
        label="Closing rate"
        value={totals.end_rate.toFixed(4)}
        hint="Latest published business day in range"
        icon={<LineChart size={18} />}
      />
      <MetricCard
        label="Period change"
        value={formatPct(totals.total_pct_change)}
        hint="Movement from opening to closing rate"
        icon={
          totals.total_pct_change && totals.total_pct_change < 0 ? (
            <ArrowDownRight size={18} />
          ) : (
            <ArrowUpRight size={18} />
          )
        }
        accent={changeAccent}
      />
      <MetricCard
        label="Average rate"
        value={totals.mean_rate.toFixed(4)}
        hint="Mean across all published days"
        icon={<Sigma size={18} />}
      />
    </div>
  );
}
