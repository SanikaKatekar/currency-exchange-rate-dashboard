/**
 * Tabular day-by-day FX breakdown with directional coloring.
 */
import type { DayRate } from "../types";

/** Format day-over-day percentage change for table cells. */
function formatPct(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/** CSS class for positive/negative daily movement. */
function pctClass(value: number | null): string {
  if (value === null || value === 0) return "text-[var(--text-secondary)]";
  return value > 0 ? "positive" : "negative";
}

/** Sortable-style table listing each published business day in the range. */
export function RateTable({ days }: { days: DayRate[] }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[var(--border-subtle)]">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-white/5 text-[var(--text-muted)]">
          <tr>
            <th className="px-4 py-3 font-medium">Date</th>
            <th className="px-4 py-3 font-medium">EUR → USD</th>
            <th className="px-4 py-3 font-medium">Day change</th>
          </tr>
        </thead>
        <tbody>
          {days.map((row, index) => (
            <tr
              key={row.date}
              className={index % 2 === 0 ? "bg-transparent" : "bg-white/[0.02]"}
            >
              <td className="border-t border-[var(--border-subtle)] px-4 py-3">{row.date}</td>
              <td className="border-t border-[var(--border-subtle)] px-4 py-3 font-medium">
                {row.rate.toFixed(4)}
              </td>
              <td className={`border-t border-[var(--border-subtle)] px-4 py-3 ${pctClass(row.pct_change)}`}>
                {formatPct(row.pct_change)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
