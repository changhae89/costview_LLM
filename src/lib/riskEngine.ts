import type { RiskLevel } from "@/lib/types";

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  1: "주의",
  2: "경계",
  3: "높음",
  4: "위험",
  5: "심각",
};

export const RISK_LEVEL_COLORS: Record<RiskLevel, string> = {
  1: "slate",
  2: "yellow",
  3: "orange",
  4: "red",
  5: "rose",
};

/**
 * GPR 수치를 CostView 위기 레벨로 변환합니다.
 *
 * @param gpr - Geopolitical Risk 지수
 * @returns 1~5 범위의 위험 레벨
 */
export function getRiskLevelFromGpr(gpr: number): RiskLevel {
  if (gpr >= 250) {
    return 5;
  }

  if (gpr >= 200) {
    return 4;
  }

  if (gpr >= 150) {
    return 3;
  }

  if (gpr >= 120) {
    return 2;
  }

  return 1;
}

/**
 * 위험 레벨에 대응하는 Tailwind 색상 키를 반환합니다.
 *
 * @param level - 1~5 범위의 위험 레벨
 * @returns UI에 사용할 색상 키
 */
export function getRiskColor(level: RiskLevel): string {
  return RISK_LEVEL_COLORS[level];
}

/**
 * 위험 레벨에 대응하는 한글 라벨을 반환합니다.
 *
 * @param level - 1~5 범위의 위험 레벨
 * @returns 사용자에게 노출할 레벨 라벨
 */
export function getRiskLevelLabel(level: RiskLevel): string {
  return RISK_LEVEL_LABELS[level];
}
