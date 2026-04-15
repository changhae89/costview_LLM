from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate


REPAIR_SYSTEM_PROMPT = dedent(
    """
    깨지거나 잘린 JSON을 받으면, 뉴스 분석 맥락에 맞게 아래 스키마를 만족하는 완전한 JSON 하나만 출력하는 역할입니다.

    출력 스키마 (반드시 준수):
    {{
      "event": "사건명 한 줄 문자열",
      "mechanism": "인과 메커니즘 한 줄 문자열",
      "related_indicators": ["wti"|"usd_krw"|"gold"|"base_rate" 중 해당하는 것만],
      "reliability": 0.0~1.0 숫자,
      "reliability_reason": "신뢰도 판단 근거 한 줄 문자열",
      "time_horizon": "short"|"medium"|"long",
      "effect_chain": ["원인A", "중간단계B", "최종영향C"],
      "buffer": "완충 요인 한 줄 문자열 또는 빈 문자열",
      "leading_indicator": "leading"|"coincident"|"lagging",
      "geo_scope": "global"|"asia"|"korea",
      "effects": [
        {{
          "category": "oil|fuel|gas|energy|food|wheat|commodity|price|cost|inflation|shipping 중 하나",
          "direction": "up"|"down"|"neutral",
          "magnitude": "low"|"medium"|"high",
          "change_pct_min": 숫자,
          "change_pct_max": 숫자,
          "monthly_impact": 정수(원 단위)
        }}
      ]
    }}

    규칙:
    - JSON만 출력합니다.
    - 코드블록(```)은 금지합니다.
    - 문자열 값은 반드시 한 줄로 작성합니다.
    - 영향 근거가 약하면 effects는 빈 배열로 둘 수 있습니다.
    """
).strip()


REPAIR_USER_PROMPT = dedent(
    """
    다음은 파싱 불가능한 출력입니다. 내용을 보완해 유효한 JSON만 출력하세요.

    <<<깨진 출력>>>
    {causal_raw}

    <<<요약>>>
    {summary}
    """
).strip()


REPAIR_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", REPAIR_SYSTEM_PROMPT),
        ("human", REPAIR_USER_PROMPT),
    ]
)
