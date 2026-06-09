/**
 * Date-range and breakdown controls for the dashboard query.
 */
import { CalendarRange, Download, Search } from "lucide-react";

interface ControlPanelProps {
  start: string;
  end: string;
  breakdown: "day" | "none";
  isLoading: boolean;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  onBreakdownChange: (value: "day" | "none") => void;
  onAnalyze: () => void;
  onPreset: (days: number) => void;
  onExport?: () => void;
  canExport: boolean;
}

/** Primary filter panel for selecting the analysis window. */
export function ControlPanel({
  start,
  end,
  breakdown,
  isLoading,
  onStartChange,
  onEndChange,
  onBreakdownChange,
  onAnalyze,
  onPreset,
  onExport,
  canExport,
}: ControlPanelProps) {
  return (
    <section className="glass-panel gradient-border rounded-[2rem] p-6">
      <div className="mb-6 flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[var(--accent)]">
            <CalendarRange size={18} />
            <span className="text-sm font-medium">Analysis window</span>
          </div>
          <h2 className="font-display text-3xl font-semibold">Configure your FX study</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">
            Select a period, choose your detail level, and inspect how EUR performed against USD
            across published market days.
          </p>
        </div>
        {canExport && onExport && (
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-2xl border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]"
            onClick={onExport}
          >
            <Download size={16} />
            Export CSV
          </button>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end">
        <label className="grid gap-2 text-sm text-[var(--text-secondary)]">
          Start date
          <input
            className="rounded-2xl border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-3 text-[var(--text-primary)]"
            type="date"
            value={start}
            onChange={(event) => onStartChange(event.target.value)}
          />
        </label>
        <label className="grid gap-2 text-sm text-[var(--text-secondary)]">
          End date
          <input
            className="rounded-2xl border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-3 text-[var(--text-primary)]"
            type="date"
            value={end}
            onChange={(event) => onEndChange(event.target.value)}
          />
        </label>
        <label className="grid gap-2 text-sm text-[var(--text-secondary)]">
          Detail level
          <select
            className="rounded-2xl border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-3 text-[var(--text-primary)]"
            value={breakdown}
            onChange={(event) => onBreakdownChange(event.target.value as "day" | "none")}
          >
            <option value="day">Daily breakdown</option>
            <option value="none">Summary only</option>
          </select>
        </label>
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 rounded-2xl px-5 py-3 font-semibold text-slate-950 transition hover:opacity-90 disabled:opacity-60"
          style={{ background: "var(--gradient-brand)" }}
          disabled={isLoading}
          onClick={onAnalyze}
        >
          <Search size={16} />
          {isLoading ? "Analyzing..." : "Run analysis"}
        </button>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {[7, 30, 90].map((days) => (
          <button
            key={days}
            type="button"
            className="rounded-full border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-secondary)] transition hover:border-[var(--accent)] hover:text-[var(--text-primary)]"
            onClick={() => onPreset(days)}
          >
            Last {days} days
          </button>
        ))}
      </div>
    </section>
  );
}
