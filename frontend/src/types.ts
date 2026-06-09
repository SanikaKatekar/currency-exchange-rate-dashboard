/**
 * Shared API response types for the FX Pulse dashboard.
 */

/** Single-day EUR→USD rate with optional day-over-day change. */
export interface DayRate {
  date: string;
  rate: number;
  pct_change: number | null;
}

/** Aggregated statistics for the selected date range. */
export interface SummaryTotals {
  start_rate: number;
  end_rate: number;
  total_pct_change: number | null;
  mean_rate: number;
}

/** Full `/api/v1/summary` payload consumed by the dashboard. */
export interface SummaryResponse {
  from: string;
  to: string;
  start: string;
  end: string;
  breakdown: "day" | "none";
  days: DayRate[] | null;
  totals: SummaryTotals;
  source: string;
}
