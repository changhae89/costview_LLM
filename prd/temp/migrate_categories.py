"""causal_chains 기존 category 값을 신규 카테고리로 마이그레이션
1. CHECK 제약 교체
2. category 값 변환
"""
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from prd.config import get_database_url, load_environment

load_environment()

MIGRATION_MAP = {
    "grocery": "food",
    "dining":  "food",
    "utility": "energy",
    "clothing": "commodity",
    "travel":  "shipping",
}

NEW_ALLOWED = (
    "oil", "fuel", "gas", "energy",
    "food", "wheat", "commodity",
    "price", "cost", "inflation",
    "shipping",
)

db_url = get_database_url()
if "sslmode" not in db_url:
    db_url += ("&" if "?" in db_url else "?") + "sslmode=require"
conn = psycopg2.connect(db_url)

try:
    with conn.cursor() as cur:
        # 현재 상태 확인
        cur.execute("SELECT category, COUNT(*) FROM causal_chains GROUP BY category ORDER BY category;")
        print("마이그레이션 전:")
        for row in cur.fetchall():
            print(f"  {row[0]:15s}  {row[1]}건")

        # 1) 기존 CHECK 제약 삭제
        cur.execute("""
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'causal_chains'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) LIKE '%category%';
        """)
        constraints = cur.fetchall()
        for (conname,) in constraints:
            print(f"  DROP CONSTRAINT {conname}")
            cur.execute(f"ALTER TABLE causal_chains DROP CONSTRAINT {conname};")

        # 2) 카테고리 값 마이그레이션
        for old, new in MIGRATION_MAP.items():
            cur.execute(
                "UPDATE causal_chains SET category = %s WHERE category = %s;",
                (new, old),
            )
            print(f"  {old:10s} → {new:10s}  ({cur.rowcount}건 변경)")

        # 3) 신규 CHECK 제약 생성
        values_str = ", ".join(f"'{v}'" for v in NEW_ALLOWED)
        cur.execute(f"""
            ALTER TABLE causal_chains
            ADD CONSTRAINT causal_chains_category_check
            CHECK (category IN ({values_str}));
        """)
        print(f"  ADD CONSTRAINT causal_chains_category_check ({len(NEW_ALLOWED)}개 허용)")

        conn.commit()

        # 결과 확인
        cur.execute("SELECT category, COUNT(*) FROM causal_chains GROUP BY category ORDER BY category;")
        print("\n마이그레이션 후:")
        for row in cur.fetchall():
            print(f"  {row[0]:15s}  {row[1]}건")

finally:
    conn.close()
