import os
import sys
import unicodedata
import re
from datetime import datetime, timezone, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from dotenv import load_dotenv
from exa_py import Exa
from supabase import create_client, Client

load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not EXA_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 누락된 환경 변수가 있습니다.")
    sys.exit(1)

exa_client = Exa(api_key=EXA_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 고도화된 노이즈 제거 패턴 ---

_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(https?://[^\)]+\)")
_JS_LINK_RE = re.compile(r"\[[^\]]*\]\(javascript:[^\)]*\)")
_BARE_URL_RE = re.compile(r"https?://\S+")
_LIST_ITEM_RE = re.compile(r"^-\s+.+$", re.MULTILINE)

_UI_NOISE_PATTERNS = [
    re.compile(r"^\s*(좋아요|슬퍼요|화나요|추천|공감)\s*\d*\s*$", re.MULTILINE),
    re.compile(r"^\s*(댓글|등록|취소|확인|닫기|뒤로가기|맨위로|TOP|목록|검색)\s*$", re.MULTILINE),
    re.compile(r"^\s*(공유하기|링크 복사|네이버|카카오|페이스북|트위터)\s*$", re.MULTILINE),
    re.compile(r"^\s*(글자 크기|글씨 키우기|인쇄하기|본문 듣기|글자 설정)\s*$", re.MULTILINE),
]

_BAD_SECTION_RE = re.compile(
    r"^#+\s*(인기기사|추천기사|관련기사|가장 많이 본|핫클릭|많이 본 뉴스|실시간|포토|주요뉴스|인기 뉴스|최신뉴스).*$", 
    re.MULTILINE | re.IGNORECASE
)

_NAV_BREADCRUMB_RE = re.compile(r"^.*(홈\s*[>|]|뉴스\s*[>|]|카테고리\s*[>|]|분야별\s*[>|]).*$", re.MULTILINE)

_COPYRIGHT_PATTERNS = [
    re.compile(r"ⓒ\s*.+"),
    re.compile(r"Copyright\s*.+\d{4}", re.IGNORECASE),
    re.compile(r"무단\s*전재.*금지"),
    re.compile(r"저작권.*재배포.*금지"),
    re.compile(r"All\s*[Rr]ights?\s*[Rr]eserved"),
    re.compile(r"기사\s*제공\s*:"),
]

def clean_content(title: str, text: str) -> str:
    # 1. 저작권 라인 이후 절단
    lines = text.split("\n")
    cut_idx = len(lines)
    for i, line in enumerate(lines):
        if any(p.search(line) for p in _COPYRIGHT_PATTERNS):
            cut_idx = i
            break
    text = "\n".join(lines[:cut_idx])

    # 2. 정규식 청소
    text = _MD_LINK_RE.sub("", text)
    text = _JS_LINK_RE.sub("", text)
    text = _BARE_URL_RE.sub("", text)
    text = _BAD_SECTION_RE.sub("", text)
    text = _NAV_BREADCRUMB_RE.sub("", text)
    text = _LIST_ITEM_RE.sub("", text)
    
    for p in _UI_NOISE_PATTERNS:
        text = p.sub("", text)
        
    return text.strip()

# --- 필터링 로직 ---

def is_korean_or_english(text: str, threshold: float = 0.5) -> bool:
    if not text: return False
    target_count = 0
    total_alpha = 0
    for ch in text:
        if ch.isspace() or ch.isdigit(): continue
        total_alpha += 1
        try:
            name = unicodedata.name(ch, "")
            if name.startswith("HANGUL") or name.startswith("LATIN"):
                target_count += 1
        except ValueError:
            continue
    if total_alpha == 0: return False
    return (target_count / total_alpha) >= threshold

def is_quality_content(title: str, content: str, published_date: str | None = None) -> bool:
    if not title or not content: return False
    if published_date:
        try:
            pub_dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            if pub_dt > datetime.now(timezone.utc) + timedelta(days=1): return False
        except: pass
    if not is_korean_or_english(f"{title} {content}"): return False
    if len(content) < 100: return False
    return True

def fetch_and_store_war_news():
    query = "최근 글로벌 전쟁, 분쟁 및 지정학적 리스크 발발로 인한 원자재 가격 변동과 경제적 파장"
    print(f"🔍 '{query}' 수집 시작 (전량 지능형 노이즈 제거 적용)...")
    
    today_start = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)).isoformat()

    response = exa_client.search_and_contents(
        query=query,
        num_results=10,
        start_published_date=today_start,
        text={"max_characters": 3000}
    )
    
    inserted_count = 0
    for res in response.results:
        raw_text = res.text if res.text else ""
        cleaned_text = clean_content(res.title, raw_text)
        pub_date = getattr(res, "published_date", None)

        if not is_quality_content(res.title, cleaned_text, pub_date):
            continue

        data = {
            "title": res.title,
            "content": cleaned_text,
            "news_url": res.url,
            "keyword": ["전쟁", "geopolitics", "war"],
            "increased_items": [],
            "decreased_items": [],
        }
        if pub_date:
            data["origin_published_at"] = pub_date

        try:
            supabase.table("raw_news").upsert(data, on_conflict="news_url").execute()
            inserted_count += 1
        except Exception as e:
            print(f"⚠️ {res.url} 에러: {e}")
            
    print(f"✅ 작업 완료: {inserted_count}건의 정제된 데이터 적재됨.")

if __name__ == "__main__":
    fetch_and_store_war_news()
