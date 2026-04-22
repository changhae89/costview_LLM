import os
import sys
import uuid
from typing import Literal, List, Optional, Any, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from datetime import datetime, timezone

# 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from supabase import create_client, Client

# 한글 출력 설정
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# .env 로드 (루트의 .env 검색)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

# API Keys
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Supabase 환경변수가 설정되지 않았습니다.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- [Phase 2 Update] 상세 근거 필드가 추가된 DB 구조 ---
class CausalStep(BaseModel):
    label: str = Field(description="단계별 명칭 (예: 원유 수출 제한)")
    change: str = Field(description="예상 변동 수치 (예: -15%, +5%)")

class CausalChainDB(BaseModel):
    event: str = Field(description="핵심 사건 명칭")
    mechanism: str = Field(description="종합 인과관계 요약")
    category: Literal["fuel", "gas", "energy", "oil", "price"] = Field(description="카테고리")
    direction: Literal["up", "down"] = Field(description="최종 방향")
    magnitude: Literal["low", "medium", "high"] = Field(description="최종 강도")
    
    # [Update] 다단계 인과관계 사슬
    logic_steps: List[CausalStep] = Field(description="4~6단계의 논리적 흐름 사슬")
    
    raw_shock_percent: float
    raw_shock_rationale: str
    wallet_hit_percent: float
    transmission_time_months: int
    transmission_rationale: str
    monthly_impact: int

class ReasoningResult(BaseModel):
    title: str = Field(description="이슈를 아우르는 제목")
    chains: List[CausalChainDB] = Field(description="인과관계 체인 리스트")

# --- [추론 엔진 구축] ---
def build_reasoning_engine():
    """다단계 인과관계 사슬을 생성하는 고도화된 LLM 체인"""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    structured_llm = llm.with_structured_output(ReasoningResult)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a highly skilled economic data journalist.
Your goal is to create a 'Multi-step Causal Logic Chain' that explains exactly how a news event flows through the economy to reach a consumer's wallet.

Generation Rules:
1. logic_steps: Create 4 to 6 logical steps with specific percentage estimates for each step.
   Example: [Event A (+5%)] -> [Impact B (+2%)] -> [Reaction C (-1%)] -> [Wallet Result (+4%)]
2. Ensure the math/logic feels realistic and consistent.
3. All text in Korean."""),
        ("user", "Analyze the news and build a multi-step causal chain:\n\nTitle: {title}\nContent: {content}")
    ])
    
    return prompt | structured_llm

def run_causal_inference(limit: int = 5):
    """최신 뉴스를 가져와 실시간 분석을 수행합니다."""
    print(f"🧠 [Phase 2 Update] 최신 추론 엔진 가동 중... (대상: 최근 뉴스 {limit}건)")
    
    try:
        res = supabase.table("raw_news").select("*").order("origin_published_at", desc=True).limit(limit).execute()
        articles = res.data
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return

    if not articles:
        print("⚠️ 분석할 뉴스가 없거나 DB 연결에 실패했습니다.")
        return

    engine = build_reasoning_engine()
    total_generated = 0

    for art in articles:
        title = art.get("title", "")
        content = art.get("content", "")
        
        if len(content or "") < 100:
            continue

        print(f"🔍 상세 분석 중: {title[:50]}...")
        
        try:
            result = engine.invoke({"title": title, "content": content})
            
            for chain in result.chains:
                # DB 스키마에 맞춰 데이터 구성 (신규 필드 포함)
                chain_entry = {
                    "event": chain.event,
                    "mechanism": chain.mechanism,
                    "category": chain.category,
                    "direction": chain.direction,
                    "magnitude": chain.magnitude,
                    "logic_steps": [s.dict() for s in chain.logic_steps],
                    "raw_shock_percent": chain.raw_shock_percent,
                    "raw_shock_rationale": chain.raw_shock_rationale,
                    "wallet_hit_percent": chain.wallet_hit_percent,
                    "transmission_time_months": chain.transmission_time_months,
                    "transmission_rationale": chain.transmission_rationale,
                    "monthly_impact": chain.monthly_impact,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Supabase insert
                supabase.table("causal_chains").insert(chain_entry).execute()
                total_generated += 1
                
            print(f"  ✅ 상세 분석 완료 및 적재: '{result.title}'")
            
        except Exception as e:
            print(f"  ❌ 분석/저장 오류 (스키마 확인 필요): {e}")

    print(f"\n============================================================")
    print(f"✅ 최종 결과: 총 {total_generated}건의 상세 인과관계가 적재되었습니다.")
    print(f"============================================================")

if __name__ == "__main__":
    run_causal_inference()
