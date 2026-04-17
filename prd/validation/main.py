"""검증 실행 진입점.

실행 (저장소 루트에서 prd를 cwd로):
    cd prd && python -m validation.main
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

import os

import psycopg2

from validation.runner import print_combined_report, run_validation, run_clustered_validation, print_clustered_report

# prd/validation/.env 가장 우선, 그다음 prd/.env, 저장소 루트 .env
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent
load_dotenv(_REPO_ROOT / ".env", override=False)
load_dotenv(_HERE.parent / ".env", override=False)
load_dotenv(_HERE / ".env", override=True)

# -----------------------------------------------------------------------
# 검증 기간 설정
# -----------------------------------------------------------------------
START_DATE     = "1999-01-01"   # 시작일 (포함)
END_DATE       = "2026-01-01"   # 종료일 (미포함) — None 이면 현재까지 전체
# -----------------------------------------------------------------------
# 시차 설정: config.py의 HORIZON_MONTHS 로 제어 (기본값 1 = M+1)
# 변경 시 config.py 에서 HORIZON_MONTHS = 2 등으로 수정
# -----------------------------------------------------------------------


def _get_connection():
    """DATABASE_URL로 직접 psycopg2 연결 (Supabase 환경 포함)."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 또는 POSTGRES_URL 환경변수가 없습니다.")
    if "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn


def main() -> None:
    conn = _get_connection()
    try:
        results = []
        for h in [1, 2, 3]:
            chain_scores, analysis_scores, keyword_stats = run_validation(
                conn,
                start=START_DATE,
                end=END_DATE,
                horizon=h,
            )
            results.append((chain_scores, analysis_scores, keyword_stats, h))
        print_combined_report(results)

        for h in [1, 2, 3]:
            cluster_results = run_clustered_validation(conn, start=START_DATE, end=END_DATE, horizon=h)
            print_clustered_report(cluster_results, horizon=h)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
