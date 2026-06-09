import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SourceBadge } from "./SourceBadge";

describe("SourceBadge", () => {
  it("renders live data label", () => {
    render(<SourceBadge source="live" />);
    expect(screen.getByText("Live market data")).toBeInTheDocument();
  });

  it("renders cache labels with transparent origin", () => {
    render(<SourceBadge source="cache(live)" />);
    expect(screen.getByText("Cached live data")).toBeInTheDocument();

    render(<SourceBadge source="cache(offline)" />);
    expect(screen.getByText("Cached offline data")).toBeInTheDocument();
  });

  it("renders offline fallback label", () => {
    render(<SourceBadge source="offline_fallback" />);
    expect(screen.getByText("Offline fallback")).toBeInTheDocument();
  });
});
