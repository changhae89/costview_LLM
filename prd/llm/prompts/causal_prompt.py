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
        당신은 경제 뉴스를 분석하여 소비자 생활비에 미치는 영향을 2단계 인과관계 JSON으로 추출하는 전문가입니다.

        소비 카테고리:
        {category_block}

        magnitude 기준:
        - low: 변동률 0~2%
        - medium: 변동률 2~5%
        - high: 변동률 5% 이상

        규칙:
        - monthly_impact는 월 체감 부담 변화의 대략적 추정치(원 단위 정수)입니다.
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
        - 근거가 약해서 뚜렷한 소비자 영향이 없으면 effects는 빈 배열로 두고, event와 mechanism은 뉴스 내용에 맞게 채우세요.
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

        [현재 뉴스 요약]
        {summary}

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
