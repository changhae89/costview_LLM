import os
import sys
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
    print("❌ 누락된 환경 변수가 있습니다. (.env 파일에 EXA_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY 확인 필요)")
    sys.exit(1)

exa_client = Exa(api_key=EXA_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_store_war_news():
    # 사용자의 요청에 따라 '전쟁 관련된 뉴스'에 스코프를 제한하여 쿼리
    query = "최근 글로벌 전쟁, 분쟁 및 지정학적 리스크 발발로 인한 원자재 가격 변동과 경제적 파장"
    print(f"🔍 '{query}' (Exa 검색 중)...")
    
    response = exa_client.search_and_contents(
        query=query,
        num_results=10,
        text={"max_characters": 3000} # 수집할 본문 길이
    )
    
    print(f"총 {len(response.results)}건의 기사 수집됨. Supabase 'raw_news' 테이블 적재 시작...")
    
    inserted_count = 0
    for res in response.results:
        content_text = res.text if res.text else ""
        
        # supabase DB raw_news 스키마 구조
        data = {
            "title": res.title,
            "content": content_text,
            "news_url": res.url,
            "keyword": ["전쟁", "geopolitics", "war"], # OpenAI 로직을 붙이기 전이므로 기본 전쟁 키워드로 할당
            "increased_items": [],
            "decreased_items": [],
        }
        
        # origin_published_at Exa 데이터 파싱
        if hasattr(res, "published_date") and res.published_date:
            data["origin_published_at"] = res.published_date

        try:
            # on_conflict 속성을 이용하여 news_url 중복 시 에러를 방지하고 업데이트 처리 (Upsert)
            supabase.table("raw_news").upsert(data, on_conflict="news_url").execute()
            inserted_count += 1
        except Exception as e:
            print(f"⚠️ {res.url} 삽입 중 에러 발생: {e}")
            
    print(f"✅ 총 {inserted_count}건의 뉴스 데이터베이스(Supabase) 적재 완료!")

if __name__ == "__main__":
    fetch_and_store_war_news()
