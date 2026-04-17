"""
Exa 시맨틱 검색으로 전쟁/지정학 리스크 → 원자재/소비재 가격 변동 뉴스를 수집하여
Supabase raw_news 테이블에 정제된 상태로 적재합니다.
"""

import os
import re
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from dotenv import load_dotenv
from exa_py import Exa
from supabase import Client, create_client

load_dotenv()

# ── 환경 변수 체크 ──────────────────────────────────────────────
EXA_API_KEY = os.getenv("EXA_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY가 환경 변수에 설정되어 있지 않습니다.")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL 또는 SUPABASE_ANON_KEY가 설정되어 있지 않습니다.")

exa_client = Exa(api_key=EXA_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ── 시맨틱 쿼리 목록 (전쟁/분쟁/제재 → 가격 영향만) ─────────────
# 모든 쿼리는 전쟁·분쟁·제재·지정학 리스크가 원인인 뉴스만 가져옵니다.
SEMANTIC_QUERIES: list[dict[str, Any]] = [
    # ── 중동 전쟁 → 에너지 ──
    {
        "query": "중동 전쟁 이란 제재 호르무즈 해협 봉쇄로 국제 유가 급등 원유 가격 상승",
        "keywords": ["전쟁", "중동", "이란", "유가", "원유"],
    },
    {
        "query": "이란 이스라엘 군사 충돌 미사일 공격 중동 석유 공급 불안 유가 영향",
        "keywords": ["전쟁", "이란", "이스라엘", "석유", "유가"],
    },
    {
        "query": "이란 핵 제재 석유 수출 금지 원유 공급 감소 에너지 가격 영향",
        "keywords": ["이란", "제재", "석유", "원유", "에너지"],
    },
    # ── 후티 홍해 → 물류·유가 ──
    {
        "query": "후티 반군 홍해 선박 공격 수에즈 운하 우회 해상 물류 비용 급등",
        "keywords": ["후티", "홍해", "수에즈", "물류", "전쟁"],
    },
    {
        "query": "홍해 위기 호르무즈 해협 봉쇄 위협 해운 운임 급등 컨테이너 물류비",
        "keywords": ["홍해", "호르무즈", "해운", "운임", "전쟁"],
    },
    # ── 러시아-우크라이나 전쟁 ──
    {
        "query": "러시아 우크라이나 전쟁 천연가스 공급 차질 유럽 에너지 위기",
        "keywords": ["전쟁", "러시아", "우크라이나", "천연가스", "에너지"],
    },
    {
        "query": "우크라이나 전쟁 흑해 곡물 수출 차단 국제 밀 가격 급등 식량 위기",
        "keywords": ["전쟁", "우크라이나", "흑해", "밀", "곡물"],
    },
    {
        "query": "러시아 제재 비료 원료 수출 금지 농산물 비용 증가 식량 안보",
        "keywords": ["러시아", "제재", "비료", "농산물", "식량"],
    },
    {
        "query": "러시아 우크라이나 전쟁 비철금속 알루미늄 니켈 공급 부족 가격 급등",
        "keywords": ["전쟁", "러시아", "알루미늄", "니켈", "금속"],
    },
    # ── 미중 갈등·대만 ──
    {
        "query": "미중 갈등 대만 해협 군사 긴장 반도체 공급망 차질 희토류 수출 규제",
        "keywords": ["미중", "대만", "반도체", "희토류", "공급망"],
    },
    {
        "query": "미중 무역 전쟁 관세 보복 제재 반도체 수출 규제 공급망 재편",
        "keywords": ["미중", "무역전쟁", "관세", "제재", "반도체"],
    },
    # ── 전쟁 → 원자재 전반 ──
    {
        "query": "전쟁 분쟁 지정학 리스크 원자재 가격 급등 공급 차질 글로벌 영향",
        "keywords": ["전쟁", "분쟁", "지정학", "원자재"],
    },
    {
        "query": "전쟁 제재 여파 국제 금 가격 사상 최고 안전자산 수요 급증",
        "keywords": ["전쟁", "제재", "금", "안전자산"],
    },
    {
        "query": "전쟁 지정학 위기 국제 철강 구리 원자재 가격 변동 제조업 영향",
        "keywords": ["전쟁", "지정학", "철강", "구리", "원자재"],
    },
    # ── 전쟁 → 소비자 물가·생활비 ──
    {
        "query": "중동 전쟁 유가 상승 여파 휘발유 경유 가격 인상 물류비 소비자 물가",
        "keywords": ["전쟁", "유가", "휘발유", "물류비", "물가"],
    },
    {
        "query": "전쟁 에너지 위기 전기료 가스비 인상 에너지 가격 전가 가계 부담",
        "keywords": ["전쟁", "에너지", "전기료", "가스비", "가계"],
    },
    {
        "query": "우크라이나 전쟁 곡물 수출 차단 식료품 가격 인상 장바구니 물가",
        "keywords": ["전쟁", "우크라이나", "곡물", "식료품", "물가"],
    },
    # ── 북한·한반도 ──
    {
        "query": "북한 미사일 도발 한반도 긴장 고조 원달러 환율 급등 수입 물가 영향",
        "keywords": ["북한", "미사일", "한반도", "환율", "수입물가"],
    },
    # ── 중동 확전 시나리오 ──
    {
        "query": "중동 전면전 확전 우려 이란 사우디 석유 시설 타격 유가 폭등 시나리오",
        "keywords": ["전쟁", "중동", "확전", "석유", "유가"],
    },
    {
        "query": "가자 전쟁 이스라엘 하마스 헤즈볼라 확전 중동 원유 공급 위기",
        "keywords": ["전쟁", "가자", "이스라엘", "하마스", "원유"],
    },
]

# ── content 정제(노이즈 제거) 패턴 ────────────────────────────────

# 1) 마크다운 링크 패턴: [텍스트](URL)
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(https?://[^\)]+\)")

# 2) javascript: 링크 패턴: [가](javascript:;), [](javascript:;) 등
_JS_LINK_RE = re.compile(r"\[[^\]]*\]\(javascript:[^\)]*\)")

# 3) bare URL (http/https)
_BARE_URL_RE = re.compile(r"https?://\S+")

# 4) 관련 기사 헤더 제목 (### 또는 ## 으로 시작하는 줄)
_HEADING_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)

# 5) "- " 으로 시작하는 리스트 아이템 줄 (관련기사 목록 · 네비게이션 등)
_LIST_ITEM_RE = re.compile(r"^-\s+.+$", re.MULTILINE)

# 6) 이미지 크레딧 / 출처 표시
_IMAGE_CREDIT_RE = re.compile(
    r"^.*(게티이미지뱅크|게티이미지|뉴스1|연합뉴스|AFP|로이터"
    r"|이미지\s*=|사진\s*=|그래픽\s*=|자료\s*사진|챗\s*[Gg][Pp][Tt]).*$",
    re.MULTILINE,
)

# 7) 저작권 / 기자 바이라인 → 이 줄이 나타나면 기사 본문이 끝난 것으로 간주
_COPYRIGHT_PATTERNS = [
    re.compile(r"ⓒ\s*.+"),                                    # ⓒ 조선일보
    re.compile(r"Copyright\s*.+\d{4}", re.IGNORECASE),        # Copyright 2024 ...
    re.compile(r"무단\s*전재.*금지"),                            # 무단 전재 및 재배포 금지
    re.compile(r"저작권.*재배포.*금지"),                          # 저작권자 ~ 재배포 금지
    re.compile(r"All\s*[Rr]ights?\s*[Rr]eserved"),
]

_BYLINE_PATTERNS = [
    re.compile(r"^.*기자\s*$", re.MULTILINE),                  # 홍길동 기자
    re.compile(r"^.*특파원\s*$", re.MULTILINE),                # 홍길동 특파원
    re.compile(r"^.*기자\s*[=|]\s*\S+@\S+", re.MULTILINE),    # 홍길동 기자 = email
    re.compile(r"^\S+@\S+\.\S+\s*$", re.MULTILINE),           # email@domain.com (standalone)
]

# 8) UI 노이즈 텍스트
_UI_NOISE_PATTERNS = [
    # 반응/투표
    re.compile(r"좋아요\s*\d*\s*개?"),
    re.compile(r"슬퍼요\s*\d*\s*개?"),
    re.compile(r"화나요\s*\d*\s*개?"),
    # 댓글
    re.compile(r"댓글을\s*입력해\s*주세요"),
    re.compile(r"댓글\s*\d*"),
    re.compile(r"등록"),
    # 공유 · SNS
    re.compile(r"공유하기"),
    re.compile(r"네이버.*공유"),
    re.compile(r"카카오.*공유"),
    re.compile(r"페이스북.*공유"),
    re.compile(r"트위터.*공유"),
    re.compile(r"링크\s*복사"),
    # 폰트/인쇄 UI
    re.compile(r"글자\s*크기(\s*설정)?"),
    re.compile(r"글씨\s*키우기"),
    re.compile(r"인쇄\s*하기"),
    re.compile(r"본문\s*듣기"),
    # 기타
    re.compile(r"기사\s*제공"),
    re.compile(r"원문\s*보기"),
    re.compile(r"관련\s*기사"),
    re.compile(r"추천\s*기사"),
    re.compile(r"많이\s*본\s*뉴스"),
    re.compile(r"인기\s*기사"),
]

# 9) 홀로 남은 숫자만 있는 줄 (반응 수: 0, 12 등)
_LONE_NUMBER_RE = re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE)

# 10) 홀로 남은 한 글자 줄 (가 가 폰트 크기 컨트롤 잔해)
_LONE_CHAR_RE = re.compile(r"^\s*[가-힣a-zA-Z]\s*$", re.MULTILINE)


def _truncate_at_article_end(text: str) -> str:
    """
    저작권 표시나 기자 바이라인이 나타나면,
    해당 줄 이전까지만 남기고 나머지를 잘라냅니다.
    (이후에 나오는 내용은 관련기사 링크이므로 불필요)
    """
    lines = text.split("\n")
    cut_index = len(lines)  # 기본: 자르지 않음

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # 저작권 패턴 매칭 → 이 줄 포함 이후 전부 잘라냄
        for pattern in _COPYRIGHT_PATTERNS:
            if pattern.search(stripped):
                cut_index = min(cut_index, i)
                break

        # 기자 바이라인 매칭
        if cut_index > i:
            for pattern in _BYLINE_PATTERNS:
                if pattern.search(stripped):
                    cut_index = min(cut_index, i)
                    break

    if cut_index < len(lines):
        return "\n".join(lines[:cut_index])
    return text

# ── 품목 용어 (한국어 + 영어) ─────────────────────────────────────
# 기사 본문에서 어떤 품목이 올랐는지/내렸는지 추출하기 위한 사전
ITEM_TERMS_KO: list[str] = [
    # 에너지
    "유가", "원유", "석유", "천연가스", "가스", "LNG", "난방유", "경유", "휘발유",
    "등유", "디젤", "전기료", "에너지", "연료", "석탄",
    "WTI", "브렌트", "OPEC",
    # 식량 · 농산물
    "밀", "옥수수", "대두", "쌀", "곡물", "식량", "설탕", "커피", "원두",
    "코코아", "팜유", "비료", "축산", "쇠고기", "돼지고기", "식료품", "농산물",
    # 금속 · 광물
    "알루미늄", "구리", "니켈", "철강", "철광석", "아연", "주석", "리튬",
    "코발트", "희토류", "금", "은", "비철금속", "금속", "티타늄",
    # 물류 · 공급망
    "해운", "운임", "물류비", "운송비", "컨테이너", "택배비",
    # 거시경제
    "물가", "인플레이션", "CPI", "PPI", "환율", "금리", "관세",
    "수입물가", "소비자물가",
    # 유틸리티
    "전기요금", "가스비", "난방비", "수도요금",
    # 반도체 · 산업
    "반도체", "칩",
]

ITEM_TERMS_EN: list[str] = [
    "oil", "crude", "petroleum", "natural gas", "gas", "lng", "fuel",
    "diesel", "gasoline", "coal", "energy", "brent", "wti",
    "wheat", "corn", "soybean", "rice", "grain", "food", "sugar",
    "coffee", "cocoa", "fertilizer",
    "aluminum", "copper", "nickel", "steel", "iron", "zinc", "tin",
    "lithium", "cobalt", "gold", "silver", "rare earth",
    "shipping", "freight", "commodity", "price", "cost", "inflation",
    "semiconductor", "chip",
]

# ── 방향성 패턴 (한국어) ──────────────────────────────────────────
UP_PATTERNS_KO: list[re.Pattern] = [
    re.compile(r"급등"),
    re.compile(r"폭등"),
    re.compile(r"급상승"),
    re.compile(r"상승"),
    re.compile(r"올라"),
    re.compile(r"오르"),
    re.compile(r"올랐"),
    re.compile(r"치솟"),
    re.compile(r"인상"),
    re.compile(r"뛰어"),
    re.compile(r"뛰었"),
    re.compile(r"높아"),
    re.compile(r"비싸"),
    re.compile(r"최고치"),
    re.compile(r"최고가"),
    re.compile(r"사상.*최고"),
    re.compile(r"강세"),
]

DOWN_PATTERNS_KO: list[re.Pattern] = [
    re.compile(r"급락"),
    re.compile(r"폭락"),
    re.compile(r"급감"),
    re.compile(r"하락"),
    re.compile(r"떨어"),
    re.compile(r"내려"),
    re.compile(r"내렸"),
    re.compile(r"인하"),
    re.compile(r"낮아"),
    re.compile(r"최저"),
    re.compile(r"약세"),
    re.compile(r"싸져"),
    re.compile(r"감소"),
    re.compile(r"줄어"),
    re.compile(r"위축"),
]

# ── 방향성 패턴 (영어) ────────────────────────────────────────────
UP_PATTERNS_EN: list[re.Pattern] = [
    re.compile(r"\brise(s|n)?\b", re.IGNORECASE),
    re.compile(r"\bincrease(s|d)?\b", re.IGNORECASE),
    re.compile(r"\bjump(s|ed)?\b", re.IGNORECASE),
    re.compile(r"\bsurge(s|d)?\b", re.IGNORECASE),
    re.compile(r"\bsoar(s|ed)?\b", re.IGNORECASE),
    re.compile(r"\bhigh(er)?\b", re.IGNORECASE),
    re.compile(r"\bclimb(s|ed)?\b", re.IGNORECASE),
    re.compile(r"\bspike(s|d)?\b", re.IGNORECASE),
    re.compile(r"\brall(y|ied)\b", re.IGNORECASE),
    re.compile(r"\bskyrocket", re.IGNORECASE),
]

DOWN_PATTERNS_EN: list[re.Pattern] = [
    re.compile(r"\bfall(s|en)?\b", re.IGNORECASE),
    re.compile(r"\bdrop(s|ped)?\b", re.IGNORECASE),
    re.compile(r"\bdecline(s|d)?\b", re.IGNORECASE),
    re.compile(r"\bslump(s|ed)?\b", re.IGNORECASE),
    re.compile(r"\bplunge(s|d)?\b", re.IGNORECASE),
    re.compile(r"\btumble(s|d)?\b", re.IGNORECASE),
    re.compile(r"\bcrash(es|ed)?\b", re.IGNORECASE),
    re.compile(r"\bcollaps(e|ed)\b", re.IGNORECASE),
    re.compile(r"\blower(ed)?\b", re.IGNORECASE),
    re.compile(r"\bplummet", re.IGNORECASE),
]

ALL_UP_PATTERNS = UP_PATTERNS_KO + UP_PATTERNS_EN
ALL_DOWN_PATTERNS = DOWN_PATTERNS_KO + DOWN_PATTERNS_EN

# 문장 분리 (한국어: 다/다. · 영어: .!?)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[\u3002\.\!\?\ub2e4])\s+")


def _find_items_in_text(text: str) -> set[str]:
    """text 안에 등장하는 품목 용어들을 반환합니다."""
    found: set[str] = set()
    for term in ITEM_TERMS_KO:
        if term in text:
            found.add(term)
    lower = text.lower()
    for term in ITEM_TERMS_EN:
        if re.search(rf"\b{re.escape(term)}(s)?\b", lower):
            found.add(term)
    return found


def extract_directional_items(title: str, content: str) -> dict[str, list[str] | None]:
    """
    기사 제목+본문을 문장 단위로 분석하여,
    같은 문장에서 품목어 + 상승/하락 방향어가 함께 등장하는 경우를 추출합니다.

    Returns:
        {
            "increased_items": [...] or None,
            "decreased_items": [...] or None,
        }
    Guardian loader의 extract_directional_items 로직과 동일한 방식입니다.
    """
    text = f"{title}. {content}"
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]

    increased: set[str] = set()
    decreased: set[str] = set()
    up_hits = 0
    down_hits = 0

    for sentence in sentences:
        has_up = any(p.search(sentence) for p in ALL_UP_PATTERNS)
        has_down = any(p.search(sentence) for p in ALL_DOWN_PATTERNS)
        if not (has_up or has_down):
            continue

        sentence_items = _find_items_in_text(sentence)
        if not sentence_items:
            continue

        if has_up and not has_down:
            increased.update(sentence_items)
            up_hits += 1
        elif has_down and not has_up:
            decreased.update(sentence_items)
            down_hits += 1
        # 양쪽 모두 있으면 무시 (모호한 문장)

    # 겹치는 품목 제거
    overlap = increased & decreased
    if overlap:
        increased -= overlap
        decreased -= overlap

    # 양쪽 다 남아있으면 우세한 쪽만 유지
    if increased and decreased:
        if up_hits > down_hits:
            decreased.clear()
        elif down_hits > up_hits:
            increased.clear()
        else:
            if len(increased) >= len(decreased):
                decreased.clear()
            else:
                increased.clear()

    inc = sorted(increased) if increased else None
    dec = sorted(decreased) if decreased else None
    return {"increased_items": inc, "decreased_items": dec}


def clean_content(title: str, raw_content: str) -> str:
    """
    Exa에서 가져온 raw 본문에서 노이즈를 제거합니다:
    - title 중복 제거
    - 저작권/기자 바이라인 이후 전부 잘라내기 (기사 끝 판단)
    - javascript 링크, 마크다운 링크, bare URL 제거
    - 관련기사 제목(###), 리스트 아이템(- ) 제거
    - 반응/댓글/공유/폰트 UI 텍스트 제거
    - 이미지 크레딧, 홀로 남은 숫자/글자 제거
    - 연속 빈 줄 압축
    """
    text = raw_content

    # title 중복 제거 (본문 시작 부분에 title이 그대로 나오는 경우)
    if title:
        escaped_title = re.escape(title.strip())
        text = re.sub(
            rf"^\s*{escaped_title}\s*\n?", "", text, count=1, flags=re.MULTILINE
        )

    # ★ 핵심: 저작권/기자 바이라인 이후 잘라내기 (관련기사 제거)
    text = _truncate_at_article_end(text)

    # javascript: 링크 제거 ([가](javascript:;) 등)
    text = _JS_LINK_RE.sub("", text)

    # 마크다운 링크 제거
    text = _MD_LINK_RE.sub("", text)

    # bare URL 제거
    text = _BARE_URL_RE.sub("", text)

    # ### 헤딩 라인 제거
    text = _HEADING_RE.sub("", text)

    # 리스트 아이템 줄 제거 (- 으로 시작하는 줄)
    text = _LIST_ITEM_RE.sub("", text)

    # 이미지 크레딧 제거
    text = _IMAGE_CREDIT_RE.sub("", text)

    # UI 노이즈 패턴 제거
    for pattern in _UI_NOISE_PATTERNS:
        text = pattern.sub("", text)

    # 홀로 남은 숫자 줄 제거 (반응 수: 0, 3 등)
    text = _LONE_NUMBER_RE.sub("", text)

    # 홀로 남은 한 글자 줄 제거 (가 가 폰트 컨트롤 잔해)
    text = _LONE_CHAR_RE.sub("", text)

    # 연속된 빈 줄/공백 줄 압축
    text = re.sub(r"\n\s*\n", "\n\n", text)

    # 앞뒤 공백 정리
    text = text.strip()

    return text


# ── 언어/품질 검증 ────────────────────────────────────────────────

# 일본어(히라가나/카타카나), 키릴 문자(러시아), 아랍, 태국, 중국 간체 등
_NON_TARGET_SCRIPTS = {
    "HIRAGANA", "KATAKANA", "CJK UNIFIED IDEOGRAPHS",  # 일본어/중국어
    "CYRILLIC",                                         # 러시아어
    "ARABIC",                                            # 아랍어
    "THAI",                                              # 태국어
    "DEVANAGARI",                                        # 힌디어
}

# 깨진 텍스트 및 네비게이션 패턴: 마크다운 테이블 잔해, 메뉴, 뉴스레터, 에러 메시지 등
_GARBAGE_RE = re.compile(
    r"(\|\s*-{2,}\s*\|){2,}"        # | --- | --- | 테이블 구분선
    r"|^\s*::+\s*$"                  # :: 만 있는 줄
    r"|^\s*\|\s*\|\s*$"              # | | 만 있는 줄
    r"|残り\d+文字"                   # 일본어 유료기사 잔여 글자수
    r"|有料会員限定"                   # 일본어 유료기사
    r"|Preskočiť"                    # 슬로바키아어
    r"|Напетие|прелив"               # 불가리아/러시아어
    r"|NEWSLETTER"                   # 뉴스레터 폼
    r"|Join the GlobalSecurity"      # 특정 사이트 노이즈
    r"|mailing list"                 # 메일링 리스트
    r"|Your Email Address"           # 이메일 입력
    r"|error occurred"               # 서버 에러 지시문
    r"|메뉴\s*펼치기"                 # 메뉴
    r"|기사\s*검색"                   # 검색바
    r"|검색\s*취소"                   # 검색바
    r"|로그인"                        # 로그인 UI
    r"|회원가입"                      # 회원가입 UI
    r"|반려동물"                      # 특정 사이트 무관 카테고리
,
    re.MULTILINE | re.IGNORECASE,
)

# 너무 짧거나 무의미한 제목 (뉴스사 이름만 있는 경우 등)
_GENERIC_TITLES = {
    "서울신문", "동아일보", "조선일보", "중앙일보", "매일경제", "한국경제",
    "부산파이낸셜뉴스", "파이낸셜뉴스", "연합뉴스", "경향신문", "한겨레",
}



def is_korean_or_english(text: str, threshold: float = 0.5) -> bool:
    """
    텍스트가 한국어 또는 영어인지 유니코드 블록 분석으로 판별합니다.
    한국어(HANGUL) + 영어(LATIN) + 숫자 + 공백 비율이 threshold 이상이면 True.
    """
    if not text:
        return False

    target_count = 0
    non_target_count = 0
    total_alpha = 0

    for ch in text:
        if ch.isspace() or ch.isdigit():
            continue
        total_alpha += 1

        try:
            name = unicodedata.name(ch, "")
        except ValueError:
            non_target_count += 1
            continue

        if name.startswith("HANGUL") or name.startswith("LATIN"):
            target_count += 1
        elif any(name.startswith(script) for script in _NON_TARGET_SCRIPTS):
            non_target_count += 1

    if total_alpha == 0:
        return False

    return (target_count / total_alpha) >= threshold


def is_quality_content(title: str, content: str, published_date: str | None = None) -> bool:
    """
    기사의 언어, 날짜, 품질을 검증합니다.
    - 한국어/영어가 아니면 False
    - 미래 날짜면 False
    - 제목이 너무 일반적이면 False
    - 깨진 텍스트(테이블 잔해, 네비게이션)가 많으면 False
    """
    if not title or not content:
        return False

    # 1. 미래 날짜 검증
    if published_date:
        try:
            # ISO 형식 가정 (2026-04-20T...)
            pub_dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            if pub_dt > now_dt + timedelta(days=1):  # 시차 고려 1일 여유
                return False
        except Exception:
            pass

    # 2. 제목 검증
    clean_title = title.strip()
    if clean_title in _GENERIC_TITLES:
        return False

    combined = f"{title} {content}"

    # 3. 언어 검증
    if not is_korean_or_english(combined):
        return False

    # 4. 깨진 텍스트 / 네비게이션 검증
    # 본문에 가비지 패턴이 발견되면 False
    if _GARBAGE_RE.search(content):
        return False

    # 5. 본문 내용성 검증 (정제 후 너무 짧거나 네비게이션 용어 위주인 경우)
    # 한글/영문 글자 수가 전체에서 너무 적으면 가비지로 판단
    total_len = len(content)
    if total_len < 50:  # 너무 짧음
        return False

    return True


def fetch_economic_news(
    semantic_query: str,
    num_results: int = 10,
    max_chars: int = 3000,
    start_published_date: str | None = None,
) -> List[Dict[str, Any]]:
    """
    경제적 맥락(시맨틱 쿼리)을 바탕으로 Exa를 통해 다중 소스의 뉴스를 수집합니다.
    (교차 검증을 위한 기초 데이터 수집)

    Args:
        semantic_query (str): "브라질 커피 농가 가뭄 피해 상황" 등 구체적인 맥락형 질문
        num_results (int): 교차 검증을 위해 수집할 최소 기사 개수
        max_chars (int): 본문 수집 최대 글자 수
        start_published_date (str): 이 날짜 이후 기사만 수집 (ISO 8601, 예: "2026-04-16T00:00:00Z")

    Returns:
        List[Dict]: 수집된 기사의 제목, URL, 본문 하이라이트가 포함된 딕셔너리 리스트
    """
    try:
        # Cost-Vue PRD 요구사항 REQ-01(시맨틱), REQ-02(다중 소스 교차 검증) 적용
        kwargs: dict[str, Any] = {
            "query": semantic_query,
            "num_results": num_results,
            "text": {"max_characters": max_chars},
            "highlights": {"num_sentences": 5},
        }
        if start_published_date:
            kwargs["start_published_date"] = start_published_date

        response = exa_client.search_and_contents(**kwargs)

        extracted_news = []
        for result in response.results:
            news_data = {
                "title": result.title,
                "url": result.url,
                "text": result.text,  # 전체 텍스트 중 앞 max_chars 자
                "highlights": result.highlights,
                "published_date": getattr(result, "published_date", None),
                "id": result.id,
            }
            extracted_news.append(news_data)

        return extracted_news

    except Exception as e:
        print(f"❌ 데이터 수집 중 오류 발생: {str(e)}")
        return []


def fetch_and_store_all_news(
    queries: list[dict[str, Any]] | None = None,
    num_results_per_query: int = 10,
    start_published_date: str | None = None,
) -> int:
    """
    SEMANTIC_QUERIES 전체를 순회하면서 Exa로 뉴스를 수집하고,
    content를 정제한 뒤 Supabase raw_news 테이블에 upsert합니다.

    Args:
        start_published_date: 이 날짜 이후 기사만 수집.
            None이면 오늘 자정(UTC) 기준으로 자동 설정.

    Returns:
        총 적재된 행 수
    """
    # 날짜 필터 기본값: 오늘 00:00 UTC
    if start_published_date is None:
        today = datetime.now(timezone.utc).date().isoformat()
        start_published_date = f"{today}T00:00:00Z"

    queries = queries or SEMANTIC_QUERIES
    total_inserted = 0
    total_skipped = 0
    seen_urls: set[str] = set()

    print(f"📡 총 {len(queries)}개 시맨틱 쿼리 실행 시작...")
    print(f"📅 기사 수집 기준일: {start_published_date}\n")

    for idx, q_info in enumerate(queries, 1):
        query = q_info["query"]
        default_keywords = q_info.get("keywords", [])
        print(f"[{idx}/{len(queries)}] 🔍 '{query[:50]}...' (Exa 검색 중)")

        results = fetch_economic_news(
            query,
            num_results=num_results_per_query,
            start_published_date=start_published_date,
        )
        if not results:
            print(f"  ⚠️ 결과 없음, 다음 쿼리로 넘어갑니다.")
            continue

        batch: list[dict[str, Any]] = []
        for res in results:
            url = (res.get("url") or "").strip()
            if not url or url in seen_urls:
                total_skipped += 1
                continue
            seen_urls.add(url)

            title = (res.get("title") or "").strip()
            raw_content = res.get("text") or ""

            # ── content 정제 ──
            cleaned = clean_content(title, raw_content)
            if not cleaned or len(cleaned) < 30:
                total_skipped += 1
                continue

            # origin_published_at
            pub_date = res.get("published_date")

            # ── 언어/품질 검증 (한국어·영어만, 미래날짜 제외) ──
            if not is_quality_content(title, cleaned, pub_date):
                total_skipped += 1
                continue

            # ── 방향성(상승/하락) 품목 추출 ──
            directional = extract_directional_items(title, cleaned)
            inc = directional["increased_items"]
            dec = directional["decreased_items"]

            data: dict[str, Any] = {
                "title": title[:1000],
                "content": cleaned[:12000],
                "news_url": url,
                "keyword": default_keywords,
                "increased_items": inc,
                "decreased_items": dec,
            }

            if pub_date:
                data["origin_published_at"] = pub_date

            batch.append(data)

        if not batch:
            continue

        # Supabase upsert (news_url 기준 중복 방지)
        try:
            supabase.table("raw_news").upsert(
                batch, on_conflict="news_url"
            ).execute()
            total_inserted += len(batch)
            print(f"  ✅ {len(batch)}건 적재 완료")
        except Exception as e:
            print(f"  ❌ DB 적재 오류: {e}")

    print(f"\n{'='*60}")
    print(f"✅ 전체 완료: 적재={total_inserted}건, 스킵(중복/빈본문)={total_skipped}건")
    print(f"{'='*60}")
    return total_inserted


if __name__ == "__main__":
    fetch_and_store_all_news()
