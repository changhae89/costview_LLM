from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate


REPAIR_SYSTEM_PROMPT = dedent(
    """
    깨지거나 잘린 JSON을 받으면, 뉴스 분석 맥락에 맞게 스키마를 만족하는 완전한 JSON 하나만 출력하는 역할입니다.

    규칙:
    - JSON만 출력합니다.
    - 코드블록은 금지합니다.
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
