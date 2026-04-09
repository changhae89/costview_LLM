import seedChain from "@/data/chains/CHN_RUA_001.json";
import { calcImpactDate } from "@/lib/lagCalculator";
import type { ChainEvent } from "@/lib/types";

const chainEvent = seedChain as ChainEvent;

describe("calcImpactDate", () => {
  it("calculates the impact month for CHN_RUA_001", () => {
    expect(calcImpactDate("2022-02", chainEvent.timing_forecast.lag_months)).toBe(
      "2022-06",
    );
  });

  it("handles year rollover", () => {
    expect(calcImpactDate("2022-11", 4)).toBe("2023-03");
  });

  it("returns the original month when lag is zero", () => {
    expect(calcImpactDate("2022-02", 0)).toBe("2022-02");
  });

  it("throws for an invalid year-month string", () => {
    expect(() => calcImpactDate("2022/02", 4)).toThrow(
      "eventDate must follow the YYYY-MM format.",
    );
  });

  it("throws for a negative lag", () => {
    expect(() => calcImpactDate("2022-02", -1)).toThrow(
      "lagMonths must be zero or greater.",
    );
  });
});
