from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate


def _build_category_block(categories: list[dict]) -> str:
    items = categories or [{"code": "fuel", "name_ko": "연료", "keywords": ["gasoline", "diesel"]}]
    result = []
    for cat in items:
        code = cat["code"]
        name_ko = cat["name_ko"]
        kws = cat.get("keywords") or []
        kw_str = ", ".join(kws[:2]) if kws else ""
        label = f"{name_ko} ({kw_str})" if kw_str else name_ko
        result.append(f"- {code}: {label}")
    return "\n".join(result)


def _build_category_text(categories: list[dict]) -> str:
    codes = [cat["code"] for cat in categories] if categories else ["fuel"]
    return " | ".join(codes)


def _build_example_json() -> str:
    up_example = (
        "{{"
        '"event":"국제 유가 급등",'
        '"mechanism":"원유 감산과 공급 불안으로 수입 가격이 올라 소비자 연료비 부담이 커짐",'
        '"related_indicators":["wti"],'
        '"reliability":0.84,'
        '"reliability_reason":"기사에 원유 가격 급등과 소비자 부담 연결이 직접 언급됨",'
        '"time_horizon":"short",'
        '"effect_chain":["공급 불안","원유 가격 급등","소비자 연료비 상승"],'
        '"buffer":"정부 보조금 가능성",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":['
        '{{"category":"fuel","direction":"up","magnitude":"medium","change_pct_min":2.0,"change_pct_max":5.0,"monthly_impact":15000}}'
        "]"
        "}}"
    )
    down_example = (
        "{{"
        '"event":"OPEC 증산 합의로 국제 유가 하락",'
        '"mechanism":"공급 확대로 원유 수입가가 내려가 소비자 연료비 부담이 줄어듦",'
        '"related_indicators":["wti"],'
        '"reliability":0.82,'
        '"reliability_reason":"기사에 증산 합의와 유가 하락, 소비자 연료비 인하 연결이 직접 언급됨",'
        '"time_horizon":"short",'
        '"effect_chain":["공급 확대","원유 가격 하락","소비자 연료비 하락"],'
        '"buffer":"",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":['
        '{{"category":"fuel","direction":"down","magnitude":"medium","change_pct_min":-5.0,"change_pct_max":-2.0,"monthly_impact":-12000}}'
        "]"
        "}}"
    )
    return (
        "cost_signal:up 예시:\n" + up_example + "\n\ncost_signal:down 예시:\n" + down_example
    )


def build_causal_prompt(categories: list[dict]) -> ChatPromptTemplate:
    category_block = _build_category_block(categories)
    category_text = _build_category_text(categories)
    example_json = _build_example_json()

    system_prompt = dedent(
        f"""
        당신은 소비자 생활비 영향 분석 결과를 구조화된 JSON으로 변환하는 모델입니다.

        입력:
        - 현재 뉴스 압축 노트
        - 기사 시점 경제지표 요약
        - 과거 유사 기사 요약
        - 허용된 생활비 카테고리

        생활비 카테고리:
        {category_block}

        목표:
        - 생활비에 영향을 주는 직접 경로만 남깁니다.
        - 기사 근거가 약하면 보수적으로 판단합니다.
        - 반드시 유효한 JSON만 출력합니다.

        핵심 규칙:
        1. 반드시 순수 JSON만 출력합니다. 출력은 반드시 JSON 객체 시작 문자로 시작해야 합니다.
           ```json, ```, 마크다운, 설명 텍스트를 절대 포함하지 않습니다.
        2. 기사에 직접 근거가 없는 내용은 쓰지 않습니다.
        3. 정치 기사, 인물 기사, 문화 기사처럼 생활비 연결이 약하면 effects는 빈 배열로 둡니다.
        4. 현재 뉴스 요약에 cost_signal:none 또는 consumer_link:no가 보이면 effects는 기본적으로 빈 배열이어야 합니다.
        5. history_context는 참고만 합니다. 현재 기사 근거보다 우선하지 않습니다.
        6. indicator_context는 보조 근거일 뿐이며 기사 내용과 맞을 때만 사용합니다.
        7. geo_scope는 기존 저장 호환용 필드이며 global, asia, korea 중 하나만 사용합니다.
        8. article_scope는 기사 자체의 실제 지역이며 korea, uk, europe, asia, middle_east, africa, americas, global, unknown 중 하나만 사용합니다.
        9. korea_relevance는 한국 소비자 생활비와의 관련성으로 direct, indirect, none 중 하나만 사용합니다.
        10. 영국 기사면 article_scope는 uk입니다. 유럽 일반 기사면 europe입니다.
        11. 한국 과거 기사 데이터가 부족하더라도 foreign 기사를 korea로 바꾸지 않습니다.
        12. 기사 자체가 한국이거나 한국 가계 영향이 직접 명시되면 geo_scope=korea를 사용할 수 있습니다.
        13. 아시아 지역 기사지만 한국 직접 연결이 약하면 geo_scope=asia로 둡니다.
        14. 영국, 유럽, 미국, 중동, 아프리카 등 비한국 기사에서 한국 직접 연결 근거가 없으면 geo_scope=global로 둡니다.
        15. 확신이 없으면 geo_scope는 global, article_scope는 unknown으로 둡니다.
        16. effect_chain은 최대 3단계까지만 작성합니다.
        17. effects는 최대 3개까지만 작성합니다.
        18. 동일한 category 중복은 한 번만 사용합니다.
        19. related_indicators는 usd_krw, wti, gold, base_rate 중 관련 있는 것만 씁니다.
        20. reliability_reason은 짧고 직접적으로 작성합니다.
        21. 아래 경우는 생활비 관련 기사로 보지 말고 effects를 빈 배열로 둡니다.
            - 개별 주택 매매가, 개별 부동산 시세, 자산가격, 주가, 기업 인수합병, 단일 주식/예술품 가격
            - 분쟁지역의 국지적 자산가격 왜곡이나 일시적 매매가 급락
            - 화장품, 미용, 사치재, 전시, 공연, 티켓, 오락, 고가 취미 등 선택적 소비 기사
            - 특정 브랜드/제품의 과장 광고 논란만 있고 필수 생활비 항목과 직접 연결이 없는 경우
        22. 아래처럼 넓은 생활비 항목과 직접 연결될 때만 effects를 작성합니다.
            - 연료비, 에너지비, 가스비, 식비, 곡물/원자재 가격, 운송비, 공공요금, 전반적 물가, 통신비
        23. 선택적 소비 또는 자산 가치만 변한다고 보이면 effects는 빈 배열로 둡니다.
        24. "가격이 내려가면 생활비가 줄 수 있다" 같은 일반론만으로는 effects를 만들지 않습니다.
        25. 자동차 판매 가격 경쟁, 딜러 매장 경쟁, car forecourt/forecourts 문맥은 연료비 하락으로 해석하지 않습니다.
        26. 현재 뉴스 압축 노트의 cost_signal을 반드시 확인하고 effects의 direction과 일치시킵니다.
            - cost_signal: up   → direction: up
            - cost_signal: down → direction: down
            - cost_signal: none → effects: []
        27. 공급 증가, 가격 하락, 정부 보조 확대, 세금 인하, 재고 증가, 수요 감소 뉴스는 direction: down을 적극 사용합니다.
        28. 상반된 힘이 서로 상쇄되거나 효과가 2% 미만으로 미미하면 direction: neutral, magnitude: low를 사용합니다.

        direction 기준 (월간 변화율 R 기준):
        - neutral: |R| < 2% (변화가 미미하거나 상쇄되는 경우)
        - up / down: |R| >= 2%
        - 확신이 없거나 효과가 미미할 것으로 판단되면 neutral을 선택합니다.

        magnitude 기준:
        - low: 0~2%
        - medium: 2~5%
        - high: 5% 이상

        필드 규칙:
        - event, mechanism은 비우지 않습니다.
        - time_horizon: short | medium | long
        - leading_indicator: leading | coincident | lagging
        - geo_scope: global | asia | korea
        - article_scope: korea | uk | europe | asia | middle_east | africa | americas | global | unknown
        - korea_relevance: direct | indirect | none
        - effects[].category / direction / magnitude는 아래 값만 사용합니다.
          category: {category_text}
          direction: up | down | neutral
          magnitude: low | medium | high
        - direction=neutral이면 change_pct_min, change_pct_max, monthly_impact는 0으로 둡니다.
        - 확신이 낮으면 monthly_impact는 0으로 두고 reliability를 낮춥니다.
        - buffer 값이 없으면 빈 문자열("")을 사용합니다. none, null, N/A는 쓰지 않습니다.

        출력 예시:
        {example_json}
        """
    ).strip()

    user_prompt = dedent(
        """
        아래 입력을 바탕으로 생활비 영향 JSON만 출력하세요.

        [현재 뉴스 압축 노트]
        {summary}

        [기사 시점 경제지표 요약]
        {indicator_context}

        [과거 유사 기사 요약]
        {history_context}
        """
    ).strip()

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
