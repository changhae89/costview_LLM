/**
 * 사건 발생 시점과 지연 개월 수를 기반으로 소비자 체감 시작 연월을 계산합니다.
 *
 * @param eventDate - 사건 발생 연월(YYYY-MM)
 * @param lagMonths - 체감까지 걸리는 개월 수
 * @returns 체감 시작 연월(YYYY-MM)
 */
export function calcImpactDate(eventDate: string, lagMonths: number): string {
  const matches = /^(\d{4})-(\d{2})$/.exec(eventDate);

  if (!matches) {
    throw new Error("eventDate must follow the YYYY-MM format.");
  }

  const year = Number(matches[1]);
  const month = Number(matches[2]);

  if (month < 1 || month > 12) {
    throw new Error("eventDate month must be between 01 and 12.");
  }

  if (lagMonths < 0) {
    throw new Error("lagMonths must be zero or greater.");
  }

  const impactDate = new Date(Date.UTC(year, month - 1 + lagMonths, 1));
  const impactYear = impactDate.getUTCFullYear();
  const impactMonth = String(impactDate.getUTCMonth() + 1).padStart(2, "0");

  return `${impactYear}-${impactMonth}`;
}
