from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate


def _build_category_block(categories: list[dict]) -> str:
    items = categories or [{"code": "fuel", "name_ko": "fuel", "keywords": ["gasoline", "diesel"]}]
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
        '"event":"Global oil prices rise after supply disruption",'
        '"mechanism":"A supply shock lifts crude import costs and increases household fuel spending.",'
        '"related_indicators":["wti"],'
        '"reliability":0.84,'
        '"reliability_reason":"The article directly links supply disruption, oil price increases, and higher fuel costs.",'
        '"time_horizon":"short",'
        '"effect_chain":["Supply disruption","Oil price increase","Household fuel cost increase"],'
        '"buffer":"Possible government subsidy",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":[{{"category":"fuel","direction":"up","magnitude":"medium","change_pct_min":2.0,"change_pct_max":5.0,"monthly_impact":15000}}]'
        "}}"
    )
    down_example = (
        "{{"
        '"event":"Output increase pushes oil prices lower",'
        '"mechanism":"Higher supply lowers crude prices and reduces household fuel spending.",'
        '"related_indicators":["wti"],'
        '"reliability":0.82,'
        '"reliability_reason":"The article directly links higher supply, lower oil prices, and lower fuel costs.",'
        '"time_horizon":"short",'
        '"effect_chain":["Supply increase","Oil price decline","Household fuel cost decline"],'
        '"buffer":"",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":[{{"category":"fuel","direction":"down","magnitude":"medium","change_pct_min":-5.0,"change_pct_max":-2.0,"monthly_impact":-12000}}]'
        "}}"
    )
    neutral_example1 = (
        "{{"
        '"event":"Supply talks fail but no immediate price change",'
        '"mechanism":"Negotiation failure increases uncertainty, but the article does not show a clear household cost move.",'
        '"related_indicators":["wti"],'
        '"reliability":0.55,'
        '"reliability_reason":"The article mentions uncertainty but no clear pass-through to household prices.",'
        '"time_horizon":"short",'
        '"effect_chain":["Failed talks","Market uncertainty","Limited household cost effect"],'
        '"buffer":"No realized price move yet",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":[{{"category":"fuel","direction":"neutral","magnitude":"low","change_pct_min":null,"change_pct_max":null,"monthly_impact":0}}]'
        "}}"
    )
    neutral_example2 = (
        "{{"
        '"event":"Central bank holds rates unchanged",'
        '"mechanism":"Rate hold keeps borrowing costs stable but does not directly change household fuel or food prices.",'
        '"related_indicators":[],'
        '"reliability":0.45,'
        '"reliability_reason":"No direct household price number stated in the article.",'
        '"time_horizon":"medium",'
        '"effect_chain":["Rate hold","Stable borrowing costs","No direct household price change"],'
        '"buffer":"",'
        '"leading_indicator":"lagging",'
        '"geo_scope":"global",'
        '"article_scope":"americas",'
        '"korea_relevance":"none",'
        '"effects":[]'
        "}}"
    )
    neutral_example3 = (
        "{{"
        '"event":"Global commodity prices edge higher on demand optimism",'
        '"mechanism":"Marginal commodity price increase; no specific household price figure in the article.",'
        '"related_indicators":["wti"],'
        '"reliability":0.52,'
        '"reliability_reason":"Article mentions demand optimism but gives no direct household price number.",'
        '"time_horizon":"short",'
        '"effect_chain":["Demand optimism","Commodity price uptick","Uncertain household pass-through"],'
        '"buffer":"Pass-through delay and retail competition",'
        '"leading_indicator":"leading",'
        '"geo_scope":"global",'
        '"article_scope":"global",'
        '"korea_relevance":"indirect",'
        '"effects":[{{"category":"energy","direction":"neutral","magnitude":"low","change_pct_min":null,"change_pct_max":null,"monthly_impact":0}}]'
        "}}"
    )
    return (
        "cost_signal: up example (specific % figure present):\n"
        + up_example
        + "\n\ncost_signal: down example (specific % figure present):\n"
        + down_example
        + "\n\nneutral example 1 — no realized price move:\n"
        + neutral_example1
        + "\n\nneutral example 2 — macro policy, no direct household price:\n"
        + neutral_example2
        + "\n\nneutral example 3 — no specific household price number in article:\n"
        + neutral_example3
    )


def build_causal_prompt(categories: list[dict]) -> ChatPromptTemplate:
    category_block = _build_category_block(categories)
    category_text = _build_category_text(categories)
    example_json = _build_example_json()

    system_prompt = dedent(
        f"""
        You convert the article summary into structured causal JSON for consumer cost impact.

        Inputs:
        - current article summary note
        - indicator context at article date
        - historical similar article summaries
        - allowed consumer-cost categories

        Allowed categories:
        {category_block}

        Goals:
        - Focus only on direct household cost channels.
        - Be conservative when the evidence is weak.
        - Output valid JSON only.

        Hard output rules:
        1. Output a single raw JSON object only. No markdown fences, no explanation text.
        2. Use only evidence supported by the current article. History and indicators are support context, not primary evidence.
        3. If the summary shows `cost_signal:none` or `consumer_link:no`, output `effects: []`.
        4. Use only these enums:
           - direction: up | down | neutral
           - magnitude: low | medium | high
           - time_horizon: short | medium | long
           - leading_indicator: leading | coincident | lagging
           - geo_scope: global | asia | korea
           - article_scope: korea | uk | europe | asia | middle_east | africa | americas | global | unknown
           - korea_relevance: direct | indirect | none
        5. Use only these indicator codes when relevant: usd_krw, wti, gold, base_rate.
        6. Keep `effect_chain` to at most 5 short steps.
        7. Keep `effects` to at most 3 unique categories.
        8. If `buffer` is empty, use an empty string.

        Direction rules:
        9. `direction: neutral` is the DEFAULT. Use `up` or `down` only when the article provides a clear and specific number showing a household price move of 2 % or more.
        10. Read `cost_signal` first. If `cost_signal: none`, set `effects: []`.
        11. If `cost_signal: up` or `down`, still use `direction: neutral` unless ALL of the following are true:
            - The article states a specific percentage or price figure for the household cost move.
            - The move is 2 % or larger.
            - The effect reaches consumers directly, not through a long indirect chain.
            - reliability >= 0.70.
        12. Use `direction: neutral` and `magnitude: low` if ANY of the following apply:
            - The article mentions no specific % number or price change figure.
            - The effect passes through 2 or more intermediate steps before reaching consumers.
            - Opposing forces exist that may offset the impact.
            - The article is about policy discussion, forecasts, or warnings — not a realized price change.
            - geo_scope is global and the article has no explicit Korea household link.
            - reliability < 0.70.
        13. In practice, roughly 30–40 % of articles produce a clear up/down signal. The rest are neutral. Do not force up/down.
        14. Supply increase, tax cut, subsidy expansion, price cut, duty cut, and inventory increase → `down` (when rule 11 is satisfied).
        15. Supply disruption, tax increase, price rise, duty increase, import cost increase, and shortages → `up` (when rule 11 is satisfied).

        Change-percent rules:
        16. If the article explicitly states a direct household-price figure, use that number to build a conservative range.
        16a. Do not copy headline CPI, commodity prices, or producer prices directly into `change_pct` unless the article explicitly says that number is the consumer-facing price move.
        16b. If the article gives only one exact number, build a range around it (e.g. 4 % → 3.0 to 5.0).
        17. If the article does NOT provide a specific price figure, set `change_pct_min = null` and `change_pct_max = null`. Do not invent a range.
        18. For `down`, change_pct values are negative in ascending order, for example `-5.0` to `-2.0`.
        19. For `up`, change_pct values are positive in ascending order, for example `2.0` to `5.0`.
        20. For `neutral`, set `change_pct_min = null`, `change_pct_max = null`, and `monthly_impact = 0`.
        21. If you are unsure about `monthly_impact`, set it to `0`.

        Scope rules:
        21. Do not create effects for stock-market coverage, corporate earnings, M&A, asset prices, or general politics without direct household pass-through.
        22. Foreign articles should stay foreign unless the article explicitly states a direct Korea household impact.
        23. If the article is UK-specific, use `article_scope: uk`. Use `europe`, `americas`, `middle_east`, and others only when clearly supported.

        Required JSON fields:
        - event
        - mechanism
        - related_indicators
        - reliability
        - reliability_reason
        - effects
        - time_horizon
        - effect_chain
        - buffer
        - leading_indicator
        - geo_scope
        - article_scope
        - korea_relevance

        Allowed category codes:
        {category_text}

        Output examples:
        {example_json}
        """
    ).strip()

    user_prompt = dedent(
        """
        Output only the JSON object.

        [Current article summary]
        {summary}

        [Indicator context]
        {indicator_context}

        [Historical context]
        {history_context}
        """
    ).strip()

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
