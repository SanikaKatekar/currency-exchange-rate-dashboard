import { describe, expect, it } from "vitest";
import { readParams } from "./urlParams";

describe("readParams", () => {
  it("uses URL query values when present", () => {
    const params = readParams("?start=2026-06-01&end=2026-06-07&breakdown=none");
    expect(params).toEqual({
      start: "2026-06-01",
      end: "2026-06-07",
      breakdown: "none",
    });
  });

  it("falls back to defaults when query params are missing", () => {
    const params = readParams("");
    expect(params.breakdown).toBe("day");
    expect(params.start <= params.end).toBe(true);
  });
});
