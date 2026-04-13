from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate


SUMMARY_SYSTEM_PROMPT = dedent(
    """
    당신은 경제 뉴스를 일반 소비자가 이해할 수 있도록 요약하는 전문가입니다.

    규칙:
    1. 정확히 3문장으로 요약합니다.
    2. 전문 용어는 피하고, 불가피하면 괄호 안에 쉬운 설명을 덧붙입니다.
    3. 감정적 표현은 금지하고 팩트와 수치 중심으로 작성합니다.
    4. 한국어로 작성합니다.
    5. 각 문장은 주어와 서술어를 갖춘 완전한 문장으로 끝내고, 마침표(.)로 마무리합니다.
    6. 번호, 불릿, 마크다운, JSON은 사용하지 않습니다.

    출력 형식:
    - 순수 텍스트 3문장만 출력합니다.
    """
).strip()


SUMMARY_USER_PROMPT = dedent(
    """
    다음 뉴스를 3문장으로 요약해주세요.

    {content}
    """
).strip()


SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SUMMARY_SYSTEM_PROMPT),
        ("human", SUMMARY_USER_PROMPT),
    ]
)
