import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SummaryCards } from "./SummaryCards";

describe("SummaryCards", () => {
  it("shows formatted totals from the API payload", () => {
    render(
      <SummaryCards
        totals={{
          start_rate: 1.1614,
          end_rate: 1.164,
          total_pct_change: 0.22,
          mean_rate: 1.1627,
        }}
      />,
    );

    expect(screen.getByText("1.1614")).toBeInTheDocument();
    expect(screen.getByText("1.1640")).toBeInTheDocument();
    expect(screen.getByText("+0.22%")).toBeInTheDocument();
    expect(screen.getByText("1.1627")).toBeInTheDocument();
  });
});
