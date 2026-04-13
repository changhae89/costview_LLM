"""category_master 테이블 생성 + 초기 데이터 INSERT"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import psycopg2
from prd.config import get_database_url, load_environment

load_environment()

ROWS = [
    {"code": "oil",       "name_ko": "기름값",     "name_en": "Oil",          "group_code": "energy",       "keywords": ["oil", "crude", "petroleum", "opec", "barrel"],                  "sort_order": 1},
    {"code": "fuel",      "name_ko": "주유비",     "name_en": "Fuel",         "group_code": "energy",       "keywords": ["fuel", "gasoline", "petrol", "diesel"],                         "sort_order": 2},
    {"code": "gas",       "name_ko": "가스비",     "name_en": "Gas",          "group_code": "energy",       "keywords": ["gas", "natural gas", "lng", "lpg"],                             "sort_order": 3},
    {"code": "energy",    "name_ko": "전기세",     "name_en": "Energy",       "group_code": "energy",       "keywords": ["energy", "electricity", "power", "utility"],                    "sort_order": 4},
    {"code": "food",      "name_ko": "장바구니",   "name_en": "Food",         "group_code": "living",       "keywords": ["food", "grocery", "meat", "dairy", "produce"],                  "sort_order": 5},
    {"code": "wheat",     "name_ko": "쌀·밀가루",  "name_en": "Grain",        "group_code": "living",       "keywords": ["wheat", "grain", "corn", "rice", "soybean"],                    "sort_order": 6},
    {"code": "commodity", "name_ko": "생활용품",   "name_en": "Commodity",    "group_code": "living",       "keywords": ["commodity", "raw material", "iron", "steel", "cotton"],         "sort_order": 7},
    {"code": "price",     "name_ko": "물가",       "name_en": "Price",        "group_code": "economy",      "keywords": ["price", "consumer price", "cpi"],                               "sort_order": 8},
    {"code": "cost",      "name_ko": "생활비",     "name_en": "Cost",         "group_code": "economy",      "keywords": ["cost", "living cost", "expense", "wage"],                       "sort_order": 9},
    {"code": "inflation", "name_ko": "물가상승",   "name_en": "Inflation",    "group_code": "economy",      "keywords": ["inflation", "deflation", "stagflation"],                        "sort_order": 10},
    {"code": "shipping",  "name_ko": "택배·운송비","name_en": "Shipping",     "group_code": "supply_chain", "keywords": ["shipping", "freight", "logistics", "supply chain", "port"],     "sort_order": 11},
]

DDL = """
CREATE TABLE IF NOT EXISTS public.category_master (
    code        VARCHAR(20) PRIMARY KEY,
    name_ko     VARCHAR(50) NOT NULL,
    name_en     VARCHAR(50) NOT NULL,
    group_code  VARCHAR(20) NOT NULL,
    keywords    TEXT[] NOT NULL DEFAULT '{}',
    sort_order  INT NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
"""

db_url = get_database_url()
if "sslmode" not in db_url:
    db_url += ("&" if "?" in db_url else "?") + "sslmode=require"
conn = psycopg2.connect(db_url)
try:
    with conn.cursor() as cur:
        cur.execute(DDL)
        conn.commit()
        print("[OK] category_master 테이블 생성 완료")

        for row in ROWS:
            cur.execute(
                """
                INSERT INTO category_master (code, name_ko, name_en, group_code, keywords, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    name_ko    = EXCLUDED.name_ko,
                    name_en    = EXCLUDED.name_en,
                    group_code = EXCLUDED.group_code,
                    keywords   = EXCLUDED.keywords,
                    sort_order = EXCLUDED.sort_order;
                """,
                (row["code"], row["name_ko"], row["name_en"], row["group_code"], row["keywords"], row["sort_order"]),
            )
        conn.commit()
        print(f"[OK] {len(ROWS)}건 INSERT/UPDATE 완료")

        cur.execute("SELECT code, name_ko, group_code, keywords FROM category_master ORDER BY sort_order;")
        print("\n현재 데이터:")
        for r in cur.fetchall():
            print(f"  {r[0]:12s}  {r[1]:12s}  {r[2]:14s}  {r[3]}")

finally:
    conn.close()
