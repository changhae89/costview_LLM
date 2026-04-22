import os
from typing import Literal, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()

# 사용자분의 .env 입력 오타(OPEN_API_KEY)에 대한 예외 처리
open_api_key = os.getenv("OPEN_API_KEY")
if open_api_key and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = open_api_key

# --- 2단계: 데이터 구조화(스키마) 정의 --- #
class CausalChain(BaseModel):
    step1_cause: str = Field(description="[1단계] 사건의 원인 (예: 호르무즈 해협 긴장, 원두 생산지 가뭄 등)")
    step2_intermediate: str = Field(description="[2단계] 중간 파장 (예: 글로벌 해상 운임 및 유가 상승, 원두 선물 가격 폭등 등)")
    final_cost_impact: str = Field(description="[최종 비용] 내 삶/지출에 미치는 영향 (예: 주유소 휘발유 가격 및 마트 수입 농산물 가격 상승)")
    
class ReasoningResult(BaseModel):
    causal_chains: List[CausalChain] = Field(description="도출된 2-Step 인과관계 체인 리스트 (최대 2~3개)")
    risk_score: int = Field(description="사용자 지출 영향도 위험 점수 (0~100점). 0은 안전, 100은 매우 위험")
    traffic_light: Literal["초록", "노랑", "빨강"] = Field(description="위험도 점수에 따른 신호등 색상 (0-30: 초록, 31-69: 노랑, 70-100: 빨강)")
    category: Literal["에너지", "식료품", "주거·대출", "모빌리티", "기호품", "기타"] = Field(description="본 이슈로 가장 큰 영향을 받는 타겟 지출 카테고리")
    summary: str = Field(description="분석 결과 한 줄 요약 (예: 브라질 가뭄으로 인한 카페 커피 가격 인상 임박)")

def build_reasoning_agent():
    """
    수집된 텍스트 데이터를 받아 정형화된 JSON(인과관계 체인, 스코어링, 카테고리)으로 변환하는 추론 엔진
    """
    # 기획서 상의 최적 모델은 Claude 3.5 Sonnet이지만, 현재 OpenAI 설치/연동 상태에 맞추어 작성되었습니다.
    # LLM을 ChatOpenAI(또는 ChatAnthropic)로 변경하여 사용할 수 있습니다.
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # 목표 형태로 강제 (JSON Schema 정형화)
    structured_llm = llm.with_structured_output(ReasoningResult)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the 'Cost-Vue Reasoning Engine', an expert in economic analysis.
Your task is to analyze clean, filtered economic news facts and strictly extract the structured causal relationships.
Always follow the '2-Step' logic limit: Cause -> Intermediate -> Final Cost.
It must directly link the macro geopolitical or economic event to a normal consumer's daily wallet/cost impact.

Categories available: 에너지, 식료품, 주거·대출, 모빌리티, 기호품, 기타.
Traffic Light rules:
- 0~30: 초록 (Green)
- 31~69: 노랑 (Yellow)
- 70~100: 빨강 (Red)

Output the exact JSON schema requested.
All texts should be in Korean."""),
        ("user", "Here are the filtered facts to analyze:\n\n{facts}")
    ])
    
    reasoning_chain = prompt | structured_llm
    return reasoning_chain

if __name__ == "__main__":
    # 테스트용 Clean Text (1단계 마이닝 결과물이라 가정)
    test_facts = '''[Title]: 브라질 가뭄 심화로 아라비카 원두 가격 폭등
[Source]: https://example.com/news/123
[Facts]: 브라질 주요 커피 재배 지역의 강수량이 평년의 20% 수준에 그쳐 내년 수확량이 급감할 것으로 전망됩니다. 
이에 따라 뉴욕 선물 시장에서 아라비카 원두 가격이 파운드당 3달러를 돌파하여 10년래 최고치를 갱신했습니다.
국내 커피 프랜차이즈들은 원가 압박을 견디지 못하고 다음 달부터 아메리카노 가격을 300~500원 일제히 인상할 것으로 알려졌습니다.'''
    
    agent = build_reasoning_agent()
    print("[TEST] 2단계 추론 엔진 가동 중...\n")
    try:
        res = agent.invoke({"facts": test_facts})
        print("[RESULT] 추론 및 구조화 성공 (JSON 형식):")
        print(res.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}")
