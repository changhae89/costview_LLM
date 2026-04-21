"""Domain keywords for PRD news analysis pipeline."""

from prd.llm.chains.category_registry import CATEGORY_FALLBACK_MAP

_KOREAN_ECONOMIC_KEYWORDS: frozenset[str] = frozenset(CATEGORY_FALLBACK_MAP.keys())

# 영어 본문 텍스트 매칭용: generic 단어(oil, gas, food, cost, price) 제외하고 구체적 용어만 사용
_ENGLISH_ECONOMIC_KEYWORDS_STRICT: frozenset[str] = frozenset({
    "crude", "petroleum", "opec", "barrel", "wti", "brent",  # oil
    "gasoline", "petrol", "diesel",                           # fuel
    "lng", "lpg",                                             # gas
    "electricity", "utility",                                 # energy
    "grocery", "dairy", "soybean",                            # food
    "wheat", "grain", "corn",                                 # wheat
    "freight", "logistics",                                   # shipping
    "inflation", "deflation", "stagflation", "cpi",           # price/inflation
})

_KOREAN_DIRECT_COST_KEYWORDS: frozenset[str] = frozenset({
    "연료비", "기름값", "휘발유", "경유", "주유", "유류세",
    "전기요금", "가스요금", "공공요금", "난방비", "전기료", "가스비",
    "식비", "식품", "식료품", "곡물", "원자재", "물가", "인플레이션",
    "운송비", "물류", "해운", "택배비", "통신비", "세금 인상", "세금 인하",
    "공급 차질", "공급 부족", "생필품",
})

_ENGLISH_DIRECT_COST_KEYWORDS: frozenset[str] = frozenset({
    "petrol", "gasoline", "diesel", "fuel duty", "petrol duty", "gas bill",
    "electricity bill", "utility bill", "heating bill", "consumer prices",
    "cost of living", "freight", "shipping costs", "logistics costs",
    "supply shortage", "supply disruption", "food distribution",
    "grocery prices", "food prices", "tax rise", "duty cut", "duty increase",
    # 추가: 소비자 직접 체감 가능한 에너지/연료 비용
    "energy bill", "energy bills", "energy cost", "energy costs",
    "fuel price", "fuel prices", "fuel cost",
    "petrol price", "petrol prices",
    "household bills", "living costs",
    # 유가 급등/하락은 휘발유 가격에 직접 영향
    "oil price", "oil prices",
    # 원유 선물/공급 동향 → 휘발유·난방유 가격 선행지표
    "crude oil", "crude futures", "oil futures", "oil supply", "oil demand",
    "brent crude", "wti crude",
    # 에너지 가격 단독 형태 (gas bill, electricity bill 묶음 외)
    "gas prices", "gas price", "electricity prices", "electricity price",
    "power prices", "energy supplier", "utility prices",
    # 식품 가격
    "food price", "food prices", "grocery price",
})

_ENGLISH_MARKET_TOPIC_KEYWORDS: frozenset[str] = frozenset({
    "ftse", "nasdaq", "dow", "stocks", "shares", "shareholders", "investors",
    "broker", "rating", "buy", "sell", "profits", "earnings", "results",
    "blue chip", "market", "equities", "bid", "takeover", "telecom stocks",
})

_LIVE_BLOG_TITLE_PATTERNS: tuple[str, ...] = (
    "as it happened",
    "business live",
    "live updates",
    "live blog",
    "daily briefing",
    "morning wrap",
    "evening wrap",
    "weekly wrap",
)

_SUMMARY_GROUNDING_KEYWORDS: tuple[str, ...] = (
    "inflation",
    "cpi",
    "consumer prices",
    "cost of living",
    "물가",
    "인플레이션",
    "생활비",
)
