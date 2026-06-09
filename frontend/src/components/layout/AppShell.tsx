/**
 * Branded application shell with sidebar navigation and content area.
 */
import { Activity, BarChart3, Moon, Sun } from "lucide-react";
import type { ReactNode } from "react";

interface AppShellProps {
  children: ReactNode;
  theme: "dark" | "light";
  onToggleTheme: () => void;
}

/** Layout wrapper used by every page in the product shell. */
export function AppShell({ children, theme, onToggleTheme }: AppShellProps) {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[280px_1fr]">
      <aside className="glass-panel hidden border-r border-[var(--border-subtle)] lg:flex lg:flex-col">
        <div className="border-b border-[var(--border-subtle)] px-6 py-8">
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[var(--border-subtle)] px-3 py-1 text-xs uppercase tracking-[0.24em] text-[var(--accent)]">
            FX Pulse
          </div>
          <h1 className="font-display text-3xl font-bold leading-tight">
            Institutional FX Analytics
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
            Monitor EUR→USD movement, volatility, and period performance with resilient live data.
          </p>
        </div>

        <nav className="flex-1 space-y-2 px-4 py-6 text-sm">
          <div className="flex items-center gap-3 rounded-2xl bg-[var(--accent-glow)] px-4 py-3 text-[var(--text-primary)]">
            <BarChart3 size={18} />
            <span className="font-medium">Rate Intelligence</span>
          </div>
          <a
            className="flex items-center gap-3 rounded-2xl px-4 py-3 text-[var(--text-secondary)] transition hover:bg-white/5"
            href="/docs"
            target="_blank"
            rel="noreferrer"
          >
            <Activity size={18} />
            <span>API Documentation</span>
          </a>
        </nav>

        <div className="border-t border-[var(--border-subtle)] px-6 py-5 text-xs text-[var(--text-muted)]">
          Pineapple by the door — welcome in.
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 border-b border-[var(--border-subtle)] bg-[rgba(6,11,20,0.72)] px-4 py-4 backdrop-blur-xl lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <div className="lg:hidden">
              <p className="text-xs uppercase tracking-[0.24em] text-[var(--accent)]">FX Pulse</p>
              <h2 className="font-display text-2xl font-bold">EUR → USD</h2>
            </div>
            <div className="ml-auto flex items-center gap-3">
              <button
                type="button"
                className="glass-panel rounded-full px-4 py-2 text-sm text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]"
                onClick={onToggleTheme}
                aria-label="Toggle color theme"
              >
                {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              </button>
            </div>
          </div>
        </header>
        <main className="px-4 py-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
