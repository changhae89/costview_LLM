"""category_master → cost_categories 테이블명 변경"""
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from prd.config import get_database_url, load_environment

load_environment()

db_url = get_database_url()
if "sslmode" not in db_url:
    db_url += ("&" if "?" in db_url else "?") + "sslmode=require"
conn = psycopg2.connect(db_url)

try:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE category_master RENAME TO cost_categories;")
        conn.commit()
        print("[OK] category_master → cost_categories 변경 완료")

        cur.execute("SELECT code, name_ko FROM cost_categories ORDER BY sort_order;")
        for r in cur.fetchall():
            print(f"  {r[0]:12s}  {r[1]}")
finally:
    conn.close()
