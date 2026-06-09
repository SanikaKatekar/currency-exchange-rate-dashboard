/**
 * Main dashboard page composing controls, KPIs, chart, and table.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { exportCsv, fetchSummary } from "../api/client";
import { readParams } from "../lib/urlParams";
import { ControlPanel } from "../components/ControlPanel";
import { AppShell } from "../components/layout/AppShell";
import { RateChart } from "../components/RateChart";
import { RateTable } from "../components/RateTable";
import { SummaryCards } from "../components/SummaryCards";
import { LoadingSkeleton } from "../components/ui/LoadingSkeleton";
import { SourceBadge } from "../components/ui/SourceBadge";

/** Primary product surface for FX Pulse. */
export function Dashboard() {
  const initial = useMemo(() => readParams(window.location.search), []);
  const [start, setStart] = useState(initial.start);
  const [end, setEnd] = useState(initial.end);
  const [breakdown, setBreakdown] = useState<"day" | "none">(initial.breakdown);
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (document.documentElement.dataset.theme as "dark" | "light") ?? "dark",
  );

  const query = useQuery({
    queryKey: ["summary", start, end, breakdown],
    queryFn: () => fetchSummary({ start, end, breakdown }),
    enabled: start <= end,
  });

  /** Persist the current filters in the URL for shareable analysis links. */
  function syncUrl() {
    const params = new URLSearchParams({ start, end, breakdown });
    window.history.replaceState({}, "", `?${params.toString()}`);
  }

  /** Apply a quick-select lookback window. */
  function applyPreset(days: number) {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - (days - 1));
    setStart(startDate.toISOString().slice(0, 10));
    setEnd(endDate.toISOString().slice(0, 10));
  }

  /** Toggle between dark and light visual themes. */
  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
  }

  return (
    <AppShell theme={theme} onToggleTheme={toggleTheme}>
      <div className="space-y-6">
        <ControlPanel
          start={start}
          end={end}
          breakdown={breakdown}
          isLoading={query.isFetching}
          onStartChange={setStart}
          onEndChange={setEnd}
          onBreakdownChange={setBreakdown}
          onAnalyze={() => {
            if (start > end) return;
            syncUrl();
            void query.refetch();
          }}
          onPreset={applyPreset}
          onExport={query.data ? () => exportCsv(query.data!) : undefined}
          canExport={Boolean(query.data?.days?.length)}
        />

        {start > end && (
          <div
            className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-red-200"
            role="alert"
          >
            Start date must be on or before end date.
          </div>
        )}

        {query.error && (
          <div
            className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-red-200"
            role="alert"
            aria-live="polite"
          >
            {query.error.message}
          </div>
        )}

        {query.isFetching && !query.data && <LoadingSkeleton />}

        {query.data && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-[var(--text-muted)]">Current pair</p>
                <p className="font-display text-2xl font-semibold">
                  {query.data.from} → {query.data.to}
                </p>
              </div>
              <SourceBadge source={query.data.source} />
            </div>

            <SummaryCards totals={query.data.totals} />

            {query.data.days && query.data.days.length > 0 ? (
              <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                <section className="glass-panel rounded-[2rem] p-6">
                  <div className="mb-6">
                    <p className="text-sm text-[var(--text-muted)]">Trend analysis</p>
                    <h3 className="font-display text-2xl font-semibold">Rate movement over time</h3>
                  </div>
                  <RateChart days={query.data.days} />
                </section>
                <section className="glass-panel rounded-[2rem] p-6">
                  <div className="mb-6">
                    <p className="text-sm text-[var(--text-muted)]">Daily ledger</p>
                    <h3 className="font-display text-2xl font-semibold">Published business days</h3>
                  </div>
                  <RateTable days={query.data.days} />
                </section>
              </div>
            ) : (
              <section className="glass-panel rounded-[2rem] p-8 text-center">
                <h3 className="font-display text-2xl font-semibold">Summary-only view</h3>
                <p className="mt-2 text-[var(--text-secondary)]">
                  Totals are shown above. Switch detail level to daily breakdown to view chart and
                  table data.
                </p>
              </section>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
