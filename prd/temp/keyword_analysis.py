"""raw_news 전체 keyword 분석 스크립트"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from prd.common.supabase_client import create_sb
from prd.config import load_environment

load_environment()
sb = create_sb()

all_keywords = Counter()
all_increased = Counter()
all_decreased = Counter()
total = 0
offset = 0
batch = 1000

while True:
    response = (
        sb.table("raw_news")
        .select("keyword, increased_items, decreased_items")
        .range(offset, offset + batch - 1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        break

    for row in rows:
        total += 1
        for kw in (row.get("keyword") or []):
            all_keywords[kw] += 1
        for item in (row.get("increased_items") or []):
            all_increased[item] += 1
        for item in (row.get("decreased_items") or []):
            all_decreased[item] += 1

    offset += batch
    if len(rows) < batch:
        break

out_path = Path(__file__).parent / "keyword_report.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(f"전체 뉴스 건수: {total}\n\n")

    f.write(f"{'='*60}\n")
    f.write(f"keyword (상위 50개)\n")
    f.write(f"{'='*60}\n")
    for kw, cnt in all_keywords.most_common(50):
        pct = cnt / total * 100
        f.write(f"  {kw:30s}  {cnt:5d}건  ({pct:5.1f}%)\n")

    f.write(f"\n{'='*60}\n")
    f.write(f"increased_items (상위 30개)\n")
    f.write(f"{'='*60}\n")
    for item, cnt in all_increased.most_common(30):
        pct = cnt / total * 100
        f.write(f"  {item:30s}  {cnt:5d}건  ({pct:5.1f}%)\n")

    f.write(f"\n{'='*60}\n")
    f.write(f"decreased_items (상위 30개)\n")
    f.write(f"{'='*60}\n")
    for item, cnt in all_decreased.most_common(30):
        pct = cnt / total * 100
        f.write(f"  {item:30s}  {cnt:5d}건  ({pct:5.1f}%)\n")

    f.write(f"\n{'='*60}\n")
    f.write(f"전체 keyword 목록 (알파벳순)\n")
    f.write(f"{'='*60}\n")
    for kw in sorted(all_keywords.keys()):
        f.write(f"  {kw:30s}  {all_keywords[kw]:5d}건\n")

    f.write(f"\n{'='*60}\n")
    f.write(f"전체 increased_items 목록 (알파벳순)\n")
    f.write(f"{'='*60}\n")
    for item in sorted(all_increased.keys()):
        f.write(f"  {item:30s}  {all_increased[item]:5d}건\n")

    f.write(f"\n{'='*60}\n")
    f.write(f"전체 decreased_items 목록 (알파벳순)\n")
    f.write(f"{'='*60}\n")
    for item in sorted(all_decreased.keys()):
        f.write(f"  {item:30s}  {all_decreased[item]:5d}건\n")

print(f"Done -> {out_path}")
