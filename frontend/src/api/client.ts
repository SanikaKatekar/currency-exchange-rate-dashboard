/**
 * HTTP client for FX Pulse backend endpoints.
 */
import type { SummaryResponse } from "../types";

/** Base URL for API calls; empty string uses same-origin proxy in dev/prod. */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

/** Extract a human-readable message from API error payloads. */
function parseApiError(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const body = payload as Record<string, unknown>;

  if (typeof body.error === "string") {
    return body.error;
  }

  if (typeof body.detail === "string") {
    return body.detail;
  }

  if (body.detail && typeof body.detail === "object") {
    const detail = body.detail as Record<string, unknown>;
    if (detail.status === "not_ready") {
      const sampleReady = detail.sample_file_ready ? "ready" : "missing";
      const redisReady = detail.redis_ready ? "ready" : "down";
      return `Service not ready (sample file: ${sampleReady}, Redis: ${redisReady}).`;
    }
  }

  return fallback;
}

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
    throw new Error(parseApiError(payload, "Unable to load exchange rates."));
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
