/**
 * Visual indicator for API data provenance (live, cache, or offline fallback).
 */
import { CloudOff, Database, Radio } from "lucide-react";

const SOURCE_META: Record<
  string,
  { label: string; tone: string; icon: typeof Radio }
> = {
  live: { label: "Live market data", tone: "text-[var(--positive)]", icon: Radio },
  cache: { label: "Cached response", tone: "text-[var(--warning)]", icon: Database },
  offline_fallback: {
    label: "Offline fallback",
    tone: "text-[var(--negative)]",
    icon: CloudOff,
  },
};

/** Pill badge showing where the current summary data originated. */
export function SourceBadge({ source }: { source: string }) {
  const meta = SOURCE_META[source] ?? SOURCE_META.live;
  const Icon = meta.icon;

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-medium ${meta.tone}`}
    >
      <Icon size={14} />
      {meta.label}
    </span>
  );
}
