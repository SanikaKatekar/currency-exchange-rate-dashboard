/**
 * HTTP client for FX Pulse backend endpoints.
 */
import type { SummaryResponse } from "../types";

/** Base URL for API calls; empty string uses same-origin proxy in dev/prod. */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

/**
 * Fetch EUR→USD summary data for a date range.
 *
 * @throws Error when the API returns a non-2xx status.
 */
export async function fetchSummary(params: {
  start: string;
  end: string;
  breakdown: "day" | "none";
}): Promise<SummaryResponse> {
  const query = new URLSearchParams(params);
  const response = await fetch(`${API_BASE}/api/v1/summary?${query.toString()}`);
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : payload.error ?? "Unable to load exchange rates.",
    );
  }

  return payload as SummaryResponse;
}

/** Download daily rows as a CSV file for spreadsheet analysis. */
export function exportCsv(data: SummaryResponse): void {
  const rows = data.days ?? [];
  const header = "date,rate,pct_change";
  const body = rows
    .map((row) => `${row.date},${row.rate},${row.pct_change ?? ""}`)
    .join("\n");
  const blob = new Blob([`${header}\n${body}`], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `fx-pulse-${data.start}-${data.end}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
