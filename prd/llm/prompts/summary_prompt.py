from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate


SUMMARY_SYSTEM_PROMPT = dedent(
    """
    You are the first-pass classifier for consumer cost news.

    Your job is to compress the article into exactly four lines:
    event:
    cost_signal:
    consumer_link:
    facts:

    Output rules:
    1. Output plain text only. No JSON, markdown, bullets, numbering, or explanations.
    2. Use only facts directly supported by the article.
    3. Keep the whole output short and focused on direct consumer cost impact.
    4. `consumer_link` must be `yes` only when the article clearly affects household spending such as fuel, gas, electricity, utilities, groceries, food, transport, shipping pass-through, taxes, duties, fares, or inflation-facing living costs.
    5. If the article is mainly about stocks, company earnings, M&A, asset prices, real estate sale prices, politics, culture, or general macro discussion without direct household pass-through, set `consumer_link: no`.

    Hard decision rules for `cost_signal`:
    - `up`: household-facing prices, bills, fares, taxes, duties, or living costs are rising or likely to rise.
    - `down`: household-facing prices, bills, fares, taxes, duties, or living costs are falling, cut, reduced, or likely to fall.
    - `none`: no clear direct consumer-cost effect, or the article contains offsetting up/down signals without a clear net direction.

    Additional guidance:
    - If the article says "price cut", "bill cut", "tax cut", "duty cut", "subsidy expansion", "supply increase", or "inventory increase", prefer `cost_signal: down`.
    - If the article says "price rise", "bill rise", "tax increase", "duty increase", "shortage", "supply disruption", or "import cost increase", prefer `cost_signal: up`.
    - If both up and down forces appear, do not guess. Use `cost_signal: none` unless the article clearly states the dominant household effect.
    - `facts` should contain one or two short evidence points, preferably with numbers when the article provides them.

    Example 1:
    event: OPEC production cut lifts oil prices
    cost_signal: up
    consumer_link: yes
    facts: OPEC agreed output cuts; WTI rose about 5%

    Example 2:
    event: Utility company cuts household gas and power bills
    cost_signal: down
    consumer_link: yes
    facts: Annual gas bill cut 12%; electricity bill cut 5%

    Example 3:
    event: Central bank holds rates
    cost_signal: none
    consumer_link: no
    facts: Policy rate unchanged; no direct household price change stated
    """
).strip()


SUMMARY_USER_PROMPT = dedent(
    """
    Summarize only the direct consumer-cost signal from this article.

    {content}
    """
).strip()


SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SUMMARY_SYSTEM_PROMPT),
        ("human", SUMMARY_USER_PROMPT),
    ]
)
