"""raw_news content 컬럼 샘플 확인 스크립트 → temp/content_sample.txt 에 저장"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from prd.common.supabase_client import create_sb
from prd.config import load_environment

load_environment()
sb = create_sb()

response = (
    sb.table("raw_news")
    .select("id, title, content, keyword, increased_items, decreased_items")
    .order("created_at", desc=True)
    .limit(5)
    .execute()
)

out_path = Path(__file__).parent / "content_sample.txt"
with open(out_path, "w", encoding="utf-8") as f:
    for i, row in enumerate(response.data or [], 1):
        content = row.get("content", "")
        f.write(f"\n{'='*80}\n")
        f.write(f"[{i}] 제목: {row.get('title', '')[:100]}\n")
        f.write(f"    id: {row.get('id')}\n")
        f.write(f"    keyword: {row.get('keyword')}\n")
        f.write(f"    increased_items: {row.get('increased_items')}\n")
        f.write(f"    decreased_items: {row.get('decreased_items')}\n")
        f.write(f"    content 길이: {len(content)}자\n")
        f.write(f"    content 전체:\n")
        f.write(f"{content}\n")

print(f"Done -> {out_path}")
