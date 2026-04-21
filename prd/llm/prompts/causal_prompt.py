from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate


def _build_category_block(categories: list[dict]) -> str:
    items = categories or [{"code": "fuel", "name_ko": "연료", "keywords": ["휘발유", "경유"]}]
    result: list[str] = []
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
        '"event":"공급 차질로 국제유가 상승",'
        '"mechanism":"공급 충격으로 원유 수입 비용이 오르고 가계 연료비 지출이 증가합니다.",'
        '"related_indicators":["wti"],'
        '"reliability":0.84,'
        '"reliability_reason":"기사가 공급 차질, 유가 상승, 연료비 인상을 직접 연결하고 구체적 수치를 제시합니다.",'
        '"time_horizon":"short",'
        '"effect_chain":["공급 차질","유가 상승","가계 연료비 증가"],'
        '"buffer":"정부 보조금 가능성",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":[{{"category":"fuel","direction":"up","magnitude":"medium","change_pct_min":2.0,"change_pct_max":5.0,"monthly_impact":15000,"raw_shock_percent":5.0,"raw_shock_rationale":"WTI 약 5% 상승 명시","transmission_time_months":1,"transmission_rationale":"국내 정유사 가격 반영 주기 약 1개월","wallet_hit_percent":3.0,"raw_shock_factors":["OPEC 감산","공급 차질"],"wallet_hit_factors":["정유사 마진","유류세 반영"],"logic_steps":[{{"step":1,"description":"OPEC 감산 합의"}},{{"step":2,"description":"WTI 5% 상승"}},{{"step":3,"description":"국내 휘발유 가격 인상"}}]}}]'
        "}}"
    )
    down_example = (
        "{{"
        '"event":"증산으로 국제유가 하락",'
        '"mechanism":"공급 증가로 원유 가격이 내리고 가계 연료비 지출이 감소합니다.",'
        '"related_indicators":["wti"],'
        '"reliability":0.82,'
        '"reliability_reason":"기사가 공급 증가, 유가 하락, 연료비 감소를 직접 연결하고 구체적 수치를 제시합니다.",'
        '"time_horizon":"short",'
        '"effect_chain":["공급 증가","유가 하락","가계 연료비 감소"],'
        '"buffer":"",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":[{{"category":"fuel","direction":"down","magnitude":"medium","change_pct_min":-5.0,"change_pct_max":-2.0,"monthly_impact":-12000,"raw_shock_percent":-5.0,"raw_shock_rationale":"WTI 약 5% 하락 명시","transmission_time_months":1,"transmission_rationale":"국내 정유사 가격 반영 주기 약 1개월","wallet_hit_percent":-3.0,"raw_shock_factors":["OPEC 증산","공급 증가"],"wallet_hit_factors":["정유사 마진 축소","유류세 반영"],"logic_steps":[{{"step":1,"description":"공급 증가"}},{{"step":2,"description":"WTI 5% 하락"}},{{"step":3,"description":"국내 휘발유 가격 인하"}}]}}]'
        "}}"
    )
    neutral_with_effects = (
        "{{"
        '"event":"공급 협상 결렬, 즉각적 가격 변동 없음",'
        '"mechanism":"협상 결렬로 불확실성이 높아졌으나 가계 비용 변화는 기사에 명시되지 않았습니다.",'
        '"related_indicators":["wti"],'
        '"reliability":0.55,'
        '"reliability_reason":"기사가 불확실성을 언급하나 가계 가격 전가 수치가 없습니다.",'
        '"time_horizon":"short",'
        '"effect_chain":["협상 결렬","시장 불확실성","가계 비용 영향 제한적"],'
        '"buffer":"아직 실현된 가격 변동 없음",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":[{{"category":"fuel","direction":"neutral","magnitude":"low","change_pct_min":null,"change_pct_max":null,"monthly_impact":0,"raw_shock_percent":0,"raw_shock_rationale":"구체적 수치 없음","transmission_time_months":1,"transmission_rationale":"불확실","wallet_hit_percent":0,"raw_shock_factors":[],"wallet_hit_factors":[],"logic_steps":[{{"step":1,"description":"협상 결렬"}},{{"step":2,"description":"불확실성 증가"}}]}}]'
        "}}"
    )
    neutral_no_effects = (
        "{{"
        '"event":"중앙은행 기준금리 동결",'
        '"mechanism":"금리 동결로 차입 비용은 유지되나 가계 연료비·식비에 직접 영향은 없습니다.",'
        '"related_indicators":[],'
        '"reliability":0.45,'
        '"reliability_reason":"기사에 가계 직접 가격 변화 수치가 없고 소비자 연결이 없습니다.",'
        '"time_horizon":"medium",'
        '"effect_chain":["금리 동결","차입 비용 안정","가계 직접 가격 변화 없음"],'
        '"buffer":"",'
        '"leading_indicator":"lagging",'
        '"geo_scope":"global",'
        '"article_scope":"americas",'
        '"korea_relevance":"none",'
        '"effects":[]'
        "}}"
    )
    return (
        "cost_signal: up 예시 (구체적 % 수치 있음, consumer_link: yes):\n"
        + up_example
        + "\n\ncost_signal: down 예시 (구체적 % 수치 있음, consumer_link: yes):\n"
        + down_example
        + "\n\nneutral 예시 1 — consumer_link: yes이나 수치 없음 → effects에 neutral 포함:\n"
        + neutral_with_effects
        + "\n\nneutral 예시 2 — consumer_link: no → effects: []:\n"
        + neutral_no_effects
    )


def build_causal_prompt(categories: list[dict]) -> ChatPromptTemplate:
    category_block = _build_category_block(categories)
    category_text = _build_category_text(categories)
    example_json = _build_example_json()

    system_prompt = dedent(
        f"""
        당신은 기사 요약을 소비자 생활비 영향 인과관계 JSON으로 변환하는 분석기입니다.

        입력:
        - 현재 기사 요약
        - 기사 날짜 기준 경제 지표 컨텍스트
        - 유사 기사 히스토리 요약
        - 허용된 소비자 비용 카테고리

        허용 카테고리:
        {category_block}

        목표:
        - 가계 직접 비용 채널에만 집중합니다.
        - 근거가 약하면 보수적으로 판단합니다.
        - 유효한 JSON만 출력합니다.
        - event, mechanism, effect_chain, reliability_reason, buffer는 반드시 한국어로 작성합니다.

        출력 규칙:
        1. 단일 JSON 객체만 출력합니다. 마크다운 펜스, 설명 텍스트 금지.
        2. 현재 기사 근거만 사용합니다. 히스토리·지표는 보조 맥락입니다.
        3. 요약의 `consumer_link: no`이면 `effects: []` 출력.
        4. 요약의 `cost_signal: none`이고 `consumer_link: yes`이면 effects에 direction: neutral 항목을 포함합니다.
        5. 요약의 `cost_signal: none`이고 `consumer_link: no`이면 `effects: []` 출력.
        5. 허용 enum만 사용합니다:
           - direction: up | down | neutral
           - magnitude: low | medium | high
           - time_horizon: short | medium | long
           - leading_indicator: leading | coincident | lagging
           - geo_scope: global | asia | korea
           - article_scope: korea | uk | europe | asia | middle_east | africa | americas | global | unknown
           - korea_relevance: direct | indirect | none
        6. 지표 코드는 관련 있을 때만 사용: usd_krw, wti, gold, base_rate
        7. `effect_chain`은 최대 5단계로 제한합니다.
        8. `effects`는 최대 3개 카테고리로 제한합니다.
        9. `buffer`가 없으면 빈 문자열을 사용합니다.
        10. `mechanism`은 2문장 이내, 100자 이내로 작성합니다.

        `korea_relevance` 판단 기준:
        - `direct`: 기사가 한국 가계 가격·세금·공급에 직접 영향을 명시한 경우
        - `indirect`: 글로벌 원자재·환율·공급망을 통해 한국에 간접 영향이 예상되는 경우
        - `none`: 한국과 무관하거나 영향 경로가 없는 경우

        `reliability` 산정 기준:
        - 0.80 이상: 기사에 구체적 수치와 직접 가계 가격 연결이 모두 있음
        - 0.60~0.79: 수치는 있으나 간접 경로이거나, 직접 연결이나 수치 중 하나만 있음
        - 0.40~0.59: 수치 없이 방향만 언급하거나 불확실성이 높음
        - 0.40 미만: 소비자 연결이 매우 약하거나 추측에 가까움

        direction 판단 규칙:
        11. `direction: neutral`이 기본값입니다. `up` 또는 `down`은 아래 조건을 모두 충족할 때만 사용합니다:
            - 기사에 가계 직접 가격 변동의 구체적 수치(%)가 있음
            - 변동폭 2% 이상
            - 소비자에게 직접 전가됨 (긴 간접 경로 아님)
            - reliability >= 0.70
        12. 아래 중 하나라도 해당하면 `direction: neutral`, `magnitude: low` 사용:
            - 기사에 구체적 % 수치나 가격 변화 없음
            - 소비자 도달까지 2단계 이상 간접 경로
            - 상쇄 요인 존재
            - 정책 논의·예측·경고 기사 (실현된 가격 변화 아님)
            - geo_scope가 global이고 한국 가계 직접 연결 없음
            - reliability < 0.70
        13. 실제로 약 30~40%의 기사만 명확한 up/down 신호를 가집니다. up/down을 강제하지 마세요.
        14. 공급 증가·세금 인하·보조금 확대·가격 인하·관세 인하·재고 증가 → `down` (규칙 11 충족 시)
        15. 공급 차질·세금 인상·가격 인상·관세 인상·수입 비용 증가·공급 부족 → `up` (규칙 11 충족 시)

        change_pct 규칙:
        16. 기사에 가계 직접 가격 수치가 명시된 경우, 그 수치를 기반으로 보수적 범위를 구성합니다.
        17. 헤드라인 CPI·원자재 가격·생산자 가격을 `change_pct`에 직접 사용하지 않습니다.
        18. 하나의 수치만 있으면 범위로 변환합니다 (예: 4% → 3.0~5.0).
        19. 기사에 구체적 가격 수치가 없으면 `change_pct_min = null`, `change_pct_max = null`.
        20. `down`이면 음수 오름차순 (예: -5.0 ~ -2.0), `up`이면 양수 오름차순 (예: 2.0 ~ 5.0).
        21. `neutral`이면 `change_pct_min = null`, `change_pct_max = null`, `monthly_impact = 0`.
        22. `monthly_impact`가 불확실하면 `0`으로 설정합니다.

        범위 규칙:
        23. 주가·기업실적·M&A·자산가격·직접 가계 전가 없는 일반 정치 기사는 effects 생성 금지.
        24. 외국 기사는 한국 가계 직접 영향이 기사에 명시된 경우에만 korea_relevance를 direct로 설정.
        25. 영국 기사는 `article_scope: uk`, 그 외 지역은 기사에 명확히 언급된 경우에만 설정.

        effects 내 각 항목 필수 필드:
        - category, direction, magnitude, change_pct_min, change_pct_max, monthly_impact
        - raw_shock_percent: 원자재 가격 충격률 (%). 수치 없으면 0.
        - raw_shock_rationale: 충격 근거 한 줄 (한국어). 수치 없으면 "구체적 수치 없음".
        - transmission_time_months: 소비자 가격 반영까지 예상 월수 (정수). short=1, medium=3, long=6.
        - transmission_rationale: 전달 시차 근거 한 줄 (한국어).
        - wallet_hit_percent: 가계 실질 부담 변화율 (%). raw_shock_percent보다 작거나 같음. 수치 없으면 0.
        - raw_shock_factors: 충격 요인 배열 (한국어, 최대 3개).
        - wallet_hit_factors: 가계 타격 요인 배열 (한국어, 최대 3개).
        - logic_steps: 추론 단계 배열. 각 항목은 step(정수)과 description(한국어) 두 키를 가진 객체. 최대 5단계.

        필수 JSON 최상위 필드:
        - event (한국어, 30자 이내)
        - mechanism (한국어, 100자 이내)
        - related_indicators
        - reliability
        - reliability_reason (한국어)
        - effects
        - time_horizon
        - effect_chain (한국어 배열, 최대 5단계)
        - buffer (한국어 또는 빈 문자열)
        - leading_indicator
        - geo_scope
        - article_scope
        - korea_relevance

        허용 카테고리 코드:
        {category_text}

        출력 예시:
        {example_json}
        """
    ).strip()

    user_prompt = dedent(
        """
        JSON 객체만 출력하세요.

        [현재 기사 요약]
        {summary}

        [경제 지표 컨텍스트]
        {indicator_context}

        [히스토리 컨텍스트]
        {history_context}
        """
    ).strip()

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
