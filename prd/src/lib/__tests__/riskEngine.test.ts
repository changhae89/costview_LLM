import seedChain from "@/data/chains/CHN_RUA_001.json";
import {
  getRiskColor,
  getRiskLevelFromGpr,
  getRiskLevelLabel,
} from "@/lib/riskEngine";
import type { ChainEvent, RiskLevel } from "@/lib/types";

const chainEvent = seedChain as ChainEvent;

describe("getRiskLevelFromGpr", () => {
  it("returns level 5 for GPR 280", () => {
    expect(getRiskLevelFromGpr(280)).toBe(5);
  });

  it.each([
    [100, 1],
    [119, 1],
    [120, 2],
    [149, 2],
    [150, 3],
    [199, 3],
    [200, 4],
    [249, 4],
    [250, 5],
  ])("maps GPR %i to level %i", (gpr, expectedLevel) => {
    expect(getRiskLevelFromGpr(gpr)).toBe(expectedLevel);
  });

  it("matches the seed data risk level", () => {
    expect(getRiskLevelFromGpr(280)).toBe(chainEvent.risk_assessment.level);
  });
});

describe("risk level metadata helpers", () => {
  it.each<[RiskLevel, string]>([
    [1, "slate"],
    [2, "yellow"],
    [3, "orange"],
    [4, "red"],
    [5, "rose"],
  ])("returns %s color for level %i", (level, expectedColor) => {
    expect(getRiskColor(level)).toBe(expectedColor);
  });

  it("returns the Korean severity label for the seed level", () => {
    expect(getRiskLevelLabel(chainEvent.risk_assessment.level)).toBe("심각");
  });
});
