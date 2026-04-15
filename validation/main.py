"""검증 실행 진입점.

실행:
    python -m validation.main
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

import os

import psycopg2

from validation.runner import print_report, run_validation

# validation/.env 우선, 루트 .env는 fallback
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
load_dotenv(_ROOT / ".env", override=False)
load_dotenv(_HERE / ".env", override=True)

# -----------------------------------------------------------------------
# 검증 기간 설정
# -----------------------------------------------------------------------
START_DATE = "1999-01-01"   # 시작일 (포함)
END_DATE   = "2000-02-01"   # 종료일 (미포함) — None 이면 현재까지 전체
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
        chain_scores, analysis_scores = run_validation(
            conn,
            start=START_DATE,
            end=END_DATE,
        )
        print_report(chain_scores, analysis_scores)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
