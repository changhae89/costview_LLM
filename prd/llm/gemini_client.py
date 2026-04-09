"""Google Gemini API client and prompt helpers for PRD analysis."""

from __future__ import annotations

import json

import google.generativeai as genai

from prd.config import get_gemini_api_key, get_gemini_model

SUMMARY_SYSTEM = """
당신은 경제 뉴스를 일반 소비자가 이해할 수 있도록 요약하는 전문가입니다.

규칙:
1. 정확히 3문장으로 요약 (더도 말고 덜도 말고)
2. 전문 용어 금지 (불가피하면 괄호 안에 쉬운 설명)
3. 감정적 표현 금지 - 팩트와 수치만
4. 한국어로 작성
5. 각 문장은 주어·서술어를 갖춘 완전한 문장으로 끝맺고, 마지막은 반드시 마침표(.)로 끝낼 것
6. 중간에 출력을 끊지 말 것 - 3문장을 모두 끝까지 작성

출력: 순수 텍스트 3문장만 (JSON 아님, 번호 매기기 없음)
""".strip()

CAUSAL_SYSTEM = """
당신은 경제 뉴스를 분석하여 소비자 생활비에 미치는 영향을
2단계 인과관계 JSON으로 추출하는 전문가입니다.

소비 카테고리:
- grocery: 장보기/마트
- dining: 외식
- fuel: 주유/교통
- utility: 공과금/에너지
- clothing: 의류/잡화
- travel: 여행/숙박

magnitude 기준:
- low: 변동률 0~2%
- medium: 변동률 2~5%
- high: 변동률 5% 이상

규칙:
- monthly_impact: 월 200만원 가구 기준 원 단위 절대값 (정수)
- 영향 없는 카테고리는 effects에 포함하지 않음
- 전망·불확실성 뉴스라도 금리·환율·심리 등으로 가계(대출 이자·생활비)에 닿을 수 있으면 간접 영향을 1개 이상 effects에 넣을 것
- effects 배열에 동일한 category·direction·수치 조합을 중복 넣지 말 것
- 변동률·monthly_impact가 모두 0에 가깝고 direction이 neutral이면 magnitude는 low
- 반드시 유효한 JSON만 출력
- related_indicators: ['usd_krw', 'wti', 'gold', 'base_rate'] 중 해당되는 것만
- event, mechanism 등 모든 문자열 값은 한 줄로만 작성
- effects[].category / direction / magnitude 는 반드시 아래 영문 소문자만:
  category: grocery | dining | fuel | utility | clothing | travel
  direction: up | down | neutral
  magnitude: low | medium | high
""".strip()

CAUSAL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "event": {"type": "string"},
        "mechanism": {"type": "string"},
        "related_indicators": {"type": "array", "items": {"type": "string"}},
        "reliability": {"type": "number"},
        "effects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "direction": {"type": "string"},
                    "magnitude": {"type": "string"},
                    "change_pct_min": {"type": "number"},
                    "change_pct_max": {"type": "number"},
                    "monthly_impact": {"type": "integer"},
                },
                "required": ["category", "direction", "magnitude"],
            },
        },
    },
    "required": ["event", "mechanism", "related_indicators", "reliability", "effects"],
}

REPAIR_SYSTEM = """
깨지거나 잘린 JSON을 받으면, 뉴스 분석 맥락에 맞게 스키마를 만족하는 완전한 JSON 하나만 출력합니다.
규칙: JSON만 출력. 코드블록 금지. 문자열 값은 반드시 한 줄(실제 줄바꿈 없음).
""".strip()

_ALLOWED_CATEGORY = frozenset({"grocery", "dining", "fuel", "utility", "clothing", "travel"})
_ALLOWED_DIRECTION = frozenset({"up", "down", "neutral"})
_ALLOWED_MAGNITUDE = frozenset({"low", "medium", "high"})
_ALLOWED_INDICATORS = frozenset({"usd_krw", "wti", "gold", "base_rate"})


def _configure_gemini() -> None:
    """Configure the Gemini SDK lazily so imports do not require configured env vars."""
    api_key = get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required.")
    genai.configure(api_key=api_key)


def _normalize_category(value) -> str | None:
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered in _ALLOWED_CATEGORY:
        return lowered
    raw = str(value).strip()
    if any(token in raw for token in ("장보기", "마트", "식료", "슈퍼", "grocery")):
        return "grocery"
    if any(token in raw for token in ("외식", "식당", "배달", "dining")):
        return "dining"
    if any(token in raw for token in ("주유", "유가", "휘발유", "경유", "교통", "fuel")):
        return "fuel"
    if any(token in raw for token in ("공과금", "전기", "가스", "난방", "에너지", "utility")):
        return "utility"
    if any(token in raw for token in ("의류", "옷", "잡화", "clothing")):
        return "clothing"
    if any(token in raw for token in ("여행", "숙박", "항공", "travel")):
        return "travel"
    if any(token in raw for token in ("이자", "금리", "대출", "채권", "가계", "주택")):
        return "utility"
    return None


def _normalize_direction(value) -> str:
    if value is None:
        return "neutral"
    lowered = str(value).strip().lower()
    if lowered in _ALLOWED_DIRECTION:
        return lowered
    raw = str(value).strip()
    if any(token in raw for token in ("상승", "인상", "증가", "오름", "up")):
        return "up"
    if any(token in raw for token in ("하락", "인하", "감소", "내림", "down")):
        return "down"
    return "neutral"


def _normalize_magnitude(value) -> str:
    if value is None:
        return "medium"
    lowered = str(value).strip().lower()
    if lowered in _ALLOWED_MAGNITUDE:
        return lowered
    raw = str(value).strip()
    if any(token in raw for token in ("낮", "소", "경미", "미미")):
        return "low"
    if any(token in raw for token in ("높", "대", "심각", "크게")):
        return "high"
    return "medium"


def _normalize_causal_for_db(causal: dict) -> dict:
    """Normalize causal output so it matches DB constraints."""
    if not isinstance(causal, dict):
        return {
            "effects": [],
            "related_indicators": [],
            "event": "",
            "mechanism": "",
            "reliability": 0.85,
        }

    output = dict(causal)
    raw_effects = output.get("effects")
    if not isinstance(raw_effects, list):
        raw_effects = []

    effects = []
    for effect in raw_effects:
        if not isinstance(effect, dict):
            continue

        category = _normalize_category(effect.get("category"))
        if category is None:
            continue

        direction = _normalize_direction(effect.get("direction"))
        magnitude = _normalize_magnitude(effect.get("magnitude"))

        try:
            change_pct_min = (
                float(effect.get("change_pct_min"))
                if effect.get("change_pct_min") is not None
                else None
            )
        except (TypeError, ValueError):
            change_pct_min = None

        try:
            change_pct_max = (
                float(effect.get("change_pct_max"))
                if effect.get("change_pct_max") is not None
                else None
            )
        except (TypeError, ValueError):
            change_pct_max = None

        try:
            monthly_impact = (
                int(effect.get("monthly_impact"))
                if effect.get("monthly_impact") is not None
                else None
            )
        except (TypeError, ValueError):
            monthly_impact = None

        if direction == "neutral" and (
            (change_pct_min is None or change_pct_min == 0)
            and (change_pct_max is None or change_pct_max == 0)
            and (monthly_impact is None or monthly_impact == 0)
        ):
            magnitude = "low"

        effects.append(
            {
                **effect,
                "category": category,
                "direction": direction,
                "magnitude": magnitude,
                "change_pct_min": change_pct_min,
                "change_pct_max": change_pct_max,
                "monthly_impact": monthly_impact,
            }
        )

    deduped_effects = []
    seen: set[tuple] = set()
    for effect in effects:
        key = (
            effect["category"],
            effect["direction"],
            effect["magnitude"],
            effect.get("change_pct_min"),
            effect.get("change_pct_max"),
            effect.get("monthly_impact"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped_effects.append(effect)

    output["effects"] = deduped_effects
    related_indicators = output.get("related_indicators")
    if isinstance(related_indicators, list):
        output["related_indicators"] = [
            str(item).strip()
            for item in related_indicators
            if str(item).strip() in _ALLOWED_INDICATORS
        ]
    else:
        output["related_indicators"] = []

    return output


async def analyze_news(news: dict) -> dict:
    """Analyze one news item into a summary and causal chain payload."""
    content = news.get("content") or news.get("title", "")
    if not content:
        raise ValueError("News content is empty.")

    summary = _call_gemini(
        system=SUMMARY_SYSTEM,
        user=f"다음 뉴스를 3문장으로 요약해주세요.\n\n{content[:3000]}",
        max_tokens=768,
        temperature=0.2,
    )

    causal_raw = _call_gemini_causal(f"뉴스 요약:\n{summary}")

    try:
        causal = _safe_parse_json(causal_raw)
    except ValueError:
        repair_user = (
            "다음은 파싱 불가능한 출력입니다. 내용을 보완해 유효한 JSON만 출력하세요.\n\n"
            f"<<<깨진 출력>>>\n{causal_raw[:4000]}\n\n"
            f"<<<요약>>>\n{summary}"
        )
        try:
            repaired = _call_gemini(
                system=REPAIR_SYSTEM,
                user=repair_user,
                max_tokens=2048,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=CAUSAL_RESPONSE_SCHEMA,
            )
        except Exception:
            repaired = _call_gemini(
                system=REPAIR_SYSTEM,
                user=repair_user,
                max_tokens=2048,
                temperature=0.1,
                response_mime_type="application/json",
            )
        causal = _safe_parse_json(repaired)

    causal = _normalize_causal_for_db(causal)
    return {"summary": summary, **causal}


def _call_gemini_causal(user: str) -> str:
    """Request structured causal JSON, retrying with a lighter config on non-quota errors."""
    try:
        return _call_gemini(
            system=CAUSAL_SYSTEM,
            user=user,
            max_tokens=2048,
            temperature=0.15,
            response_mime_type="application/json",
            response_schema=CAUSAL_RESPONSE_SCHEMA,
        )
    except Exception as error:
        message = str(error).lower()
        if "429" in message or "quota" in message or "resource exhausted" in message:
            raise
        return _call_gemini(
            system=CAUSAL_SYSTEM,
            user=user,
            max_tokens=2048,
            temperature=0.15,
            response_mime_type="application/json",
        )


def _call_gemini(
    *,
    system: str,
    user: str,
    max_tokens: int,
    response_mime_type: str | None = None,
    response_schema: dict | None = None,
    temperature: float = 0.3,
) -> str:
    """Call Gemini and return non-empty text output."""
    _configure_gemini()
    model_name = get_gemini_model()
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system,
    )

    generation_config: dict = {
        "max_output_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_mime_type:
        generation_config["response_mime_type"] = response_mime_type
    if response_schema is not None:
        generation_config["response_schema"] = response_schema

    print(
        "[prd LLM] Request - "
        f"model={model_name} max_output_tokens={max_tokens} temperature={temperature} "
        f"mime={response_mime_type or '(default)'} json_schema={'on' if response_schema else 'off'}"
    )
    print("[prd LLM] --- SYSTEM PROMPT START ---")
    print(system)
    print("[prd LLM] --- SYSTEM PROMPT END ---")
    print("[prd LLM] --- USER PROMPT START ---")
    print(user)
    print("[prd LLM] --- USER PROMPT END ---")

    response = model.generate_content(user, generation_config=generation_config)
    if not response.candidates:
        prompt_feedback = getattr(response, "prompt_feedback", None)
        raise ValueError(f"Gemini returned no candidates: {prompt_feedback}")

    text = response.text
    if not text or not text.strip():
        raise ValueError("Gemini returned an empty text response.")
    return text.strip()


def _safe_parse_json(raw: str) -> dict:
    """Parse model JSON safely, tolerating fenced code blocks and wrapped text."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:])
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].rstrip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as error:
            raise ValueError(f"JSON parse failed: {error}\nRaw:\n{raw[:500]}") from error

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON parse failed: {error}\nRaw:\n{raw[:500]}") from error
