import { describe, expect, it, vi } from "vitest";
import type { SummaryResponse } from "../types";
import { exportCsv } from "./client";

const sample: SummaryResponse = {
  from: "EUR",
  to: "USD",
  start: "2026-06-03",
  end: "2026-06-04",
  breakdown: "day",
  days: [
    { date: "2026-06-03", rate: 1.0, pct_change: null },
    { date: "2026-06-04", rate: 1.1, pct_change: 10 },
  ],
  totals: {
    start_rate: 1.0,
    end_rate: 1.1,
    total_pct_change: 10,
    mean_rate: 1.05,
  },
  source: "live",
};

describe("exportCsv", () => {
  it("downloads a CSV with header and daily rows", () => {
    const click = vi.fn();
    const anchor = { click, download: "", href: "" } as unknown as HTMLAnchorElement;
    vi.spyOn(document, "createElement").mockReturnValue(anchor);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:mock"),
      revokeObjectURL: vi.fn(),
    });

    exportCsv(sample);

    expect(document.createElement).toHaveBeenCalledWith("a");
    expect(URL.createObjectURL).toHaveBeenCalled();
    const blob = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as Blob;
    expect(blob.type).toBe("text/csv");
    expect(click).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock");
    expect(anchor.download).toBe("fx-pulse-2026-06-03-2026-06-04.csv");
  });
});
