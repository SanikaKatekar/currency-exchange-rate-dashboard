/**
 * URL query parameter helpers for dashboard filter state.
 */

/** Build a default 7-day analysis window ending today. */
export function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

/** Hydrate filter state from URL query parameters when present. */
export function readParams(search = "") {
  const params = new URLSearchParams(search);
  const defaults = defaultRange();
  return {
    start: params.get("start") ?? defaults.start,
    end: params.get("end") ?? defaults.end,
    breakdown: (params.get("breakdown") as "day" | "none") ?? "day",
  };
}
