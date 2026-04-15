from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate


def _build_category_block(categories: list[dict]) -> str:
    items = categories or [{"code": "fuel", "name_ko": "주유비", "keywords": ["gasoline", "diesel"]}]
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
    return (
        '{{'
        '"event":"호르무즈 해협 긴장 고조",'
        '"mechanism":"원유 운송 차질 우려로 국제 유가 상승 압력이 커짐",'
        '"related_indicators":["wti"],'
        '"reliability":0.82,'
        '"reliability_reason":"직접 가격 데이터 없음, 지정학적 리스크 간접 추론",'
        '"time_horizon":"short",'
        '"effect_chain":["호르무즈 해협 봉쇄 위험","국제 유가 상승","국내 유류비 상승"],'
        '"buffer":"정부 유류세 인하로 소비자 부담 일부 완충 가능",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"effects":['
        '{{"category":"fuel","direction":"up","magnitude":"medium","change_pct_min":1.0,"change_pct_max":3.0,"monthly_impact":15000}}'
        "]"
        '}}'
    )


def build_causal_prompt(categories: list[dict]) -> ChatPromptTemplate:
    category_block = _build_category_block(categories)
    category_text = _build_category_text(categories)
    example_json = _build_example_json()

    system_prompt = dedent(
        f"""
        당신은 과거 뉴스 아카이브를 분석하여 당시 소비자 생활비에 미쳤던 영향을 2단계 인과관계 JSON으로 추출하는 전문가입니다.
        뉴스는 영어 또는 한국어로 작성되어 있을 수 있습니다.
        목적은 역사적 사건이 생활비에 어떤 영향을 주었는지 데이터를 최대한 축적하는 것입니다.

        소비 카테고리:
        {category_block}

        magnitude 기준:
        - low: 변동률 0~2% (간접·불확실 영향 포함)
        - medium: 변동률 2~5%
        - high: 변동률 5% 이상

        규칙:
        - monthly_impact는 월 체감 부담 변화의 대략적 추정치(원 단위 정수)입니다.
        - 직접 영향뿐 아니라 간접 영향(전쟁 → 유가 → 연료비)도 magnitude: low로 포함하세요.
        - 불확실하거나 간접적인 영향은 reliability를 낮게(0.4~0.6) 설정하고 effects에 포함하세요.
        - 현재 뉴스 요약에 가격·비용·공급·운송·환율·원자재·인플레이션과의 직접 연결 근거가 없으면 effects=[]를 반환하세요.
        - 기술 소개, 문화·정치·역사 기사, 개인 인물 기사, 제도 일반론은 생활비 영향이 없으므로 effects=[]로 반환하세요.
        - "장기적으로 가능성 있음"만으로 효과를 추정하지 마세요. 현재 기사에 구체적 근거가 있어야 합니다.
        - effects가 완전히 빈 배열이 되는 경우는 뉴스 내용이 생활비와 전혀 무관할 때만입니다.
        - 영향이 없는 카테고리는 effects에 넣지 마세요.
        - effects 배열에 동일한 category, direction, 수치 조합을 중복해서 넣지 마세요.
        - related_indicators는 usd_krw, wti, gold, base_rate 중 해당되는 것만 사용하세요.
        - event와 mechanism은 반드시 비워두지 말고 한 줄 문자열로 작성하세요.
        - effects[].category / direction / magnitude 는 반드시 아래 값만 사용하세요.
          category: {category_text}
          direction: up | down | neutral
          magnitude: low | medium | high
        - neutral effect를 넣으려면 change_pct_min, change_pct_max, monthly_impact 중 하나 이상이 0이 아니어야 합니다.
        - direction=neutral 이고 change_pct_min=0, change_pct_max=0, monthly_impact=0 이면 그 effect는 넣지 마세요.
        - reliability_reason은 신뢰도 수치를 그렇게 판단한 이유를 한 줄로 작성하세요.
        - time_horizon은 영향이 나타나는 시간대입니다: short(1~3개월) | medium(3~12개월) | long(12개월 이상)
        - effect_chain은 파급 경로를 ["원인A", "중간단계B", "최종영향C"] 형태의 문자열 배열로 작성하세요.
        - buffer는 충격을 완충하는 요인(정부 보조금, 대체재, 비축량 등)을 한 줄로 작성하세요. 없으면 빈 문자열.
        - leading_indicator는 이 뉴스의 시장 선행성입니다: leading(가격 변화 예고) | coincident(동시 발생) | lagging(결과 보도)
        - geo_scope는 영향의 지리적 범위입니다: global | asia | korea
        - 반드시 유효한 JSON만 출력하세요.

        과거 사례 활용 규칙:
        - [과거 분석 뉴스 컨텍스트]는 참고용입니다.
        - 과거 분석을 그대로 복사하지 말고 현재 뉴스 맥락에 맞게 조정하세요.
        - 현재 뉴스 요약에 직접 근거가 있는 영향만 넣으세요.
        - 과거 분석 뉴스는 현재 뉴스보다 우선하지 않습니다.

        출력 예시:
        {example_json}
        """
    ).strip()

    user_prompt = dedent(
        """
        다음 뉴스 요약을 보고 소비자 생활비 영향 JSON만 출력하세요.
        과거 분석 뉴스는 참고용 맥락이며, 현재 뉴스보다 우선하지 마세요.
        경제 지표가 제공된 경우 monthly_impact 추정 시 실제 수치를 근거로 사용하세요.

        [현재 뉴스 요약]
        {summary}

        [뉴스 발행 당시 경제 지표]
        {indicator_context}

        [과거 분석 뉴스 컨텍스트]
        {history_context}
        """
    ).strip()

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
