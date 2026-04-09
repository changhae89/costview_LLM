"""Collect economic news with Exa semantic search."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from exa_py import Exa

_TEXT_OPTS = {"max_characters": 2200, "include_html_tags": False}

_NOISE_LINE = re.compile(
    r"(무단\s*전재|재배포\s*금지|Copyright|©\s*\d|All rights reserved|"
    r"기자\s*[:=]|^\s*기자\s|뉴스\s*제공|구독\s*하기|뉴스레터|알림\s*신청|"
    r"이\s*기사를\s*공유|SNS\s*바로가기|프로모션|광고문의|"
    r"^\[.*\]\s*$|^[■▶◆◇□]\s)",
    re.IGNORECASE | re.MULTILINE,
)

_SECTION_CUT = (
    "\n관련기사",
    "\n[관련기사",
    "\n▶",
    "\n□",
    "\n※",
    "\n【",
    "\n무단전재",
)

SEARCH_QUERIES = [
    "한국 원달러 환율 변동 생활비 영향",
    "국제유가 WTI 한국 물가 영향",
    "한국은행 기준금리 소비자물가",
    "글로벌 공급망 한국 수입 물가",
    "미국 연준 금리 결정 한국 경제",
]

TRUSTED_DOMAINS = [
    "yna.co.kr",
    "hankyung.com",
    "mk.co.kr",
    "yonhapnews.co.kr",
    "chosun.com",
    "joongang.co.kr",
]


def _get_exa_client() -> Exa:
    """Create an Exa client lazily so imports do not fail before env loading."""
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("EXA_API_KEY is required to collect news.")
    return Exa(api_key=api_key)


def _clean_article_text(raw: str) -> str:
    """Remove common footer and article-noise fragments from Exa article text."""
    if not raw or not raw.strip():
        return ""

    text = raw.strip()
    cut = len(text)
    for marker in _SECTION_CUT:
        marker_index = text.find(marker)
        if marker_index != -1 and marker_index > 120:
            cut = min(cut, marker_index)
    text = text[:cut].strip()

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped_line = line.strip()
        if len(stripped_line) < 2:
            continue
        if _NOISE_LINE.search(stripped_line):
            continue
        cleaned_lines.append(stripped_line)

    output = "\n".join(cleaned_lines).strip()
    return re.sub(r"\n{3,}", "\n\n", output)


def _body_from_item(item: object) -> str | None:
    """Extract a usable article body from Exa result text, highlights, or title."""
    text = getattr(item, "text", None)
    highlights = getattr(item, "highlights", None)
    title = getattr(item, "title", None)

    if text and text.strip():
        cleaned = _clean_article_text(text)
        if len(cleaned) < 80 and highlights:
            joined = "\n".join(highlight for highlight in highlights if highlight).strip()
            if joined:
                cleaned = _clean_article_text(joined) or joined
        if cleaned:
            return cleaned[:3000]

    if highlights:
        joined = "\n".join(highlight for highlight in highlights if highlight).strip()
        if joined:
            cleaned = _clean_article_text(joined)
            body = (cleaned or joined).strip()[:3000]
            if body:
                return body

    if title and title.strip():
        return title.strip()[:3000]

    return None


def _extract_domain(url: str) -> str:
    """Extract a normalized host from a URL string."""
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "unknown"


def _is_trusted_domain(url: str) -> bool:
    """Return whether the URL host belongs to the allowlist."""
    host = _extract_domain(url).lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in TRUSTED_DOMAINS)


async def fetch_news(
    hours_back: int = 72,
    search_queries: list[str] | None = None,
) -> list[dict[str, object]]:
    """Fetch recent economic news from Exa and return normalized records."""
    exa = _get_exa_client()
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )

    results: list[dict[str, object]] = []
    queries = search_queries or SEARCH_QUERIES

    for query in queries:
        try:
            response = exa.search_and_contents(
                query=query,
                num_results=10,
                start_published_date=since,
                text=_TEXT_OPTS,
            )
            raw_count = len(response.results)
            skipped_domain = 0
            skipped_empty = 0

            for item in response.results:
                url = getattr(item, "url", "")
                if not _is_trusted_domain(url):
                    skipped_domain += 1
                    continue

                body = _body_from_item(item)
                if not body:
                    skipped_empty += 1
                    continue

                results.append(
                    {
                        "url": url,
                        "title": getattr(item, "title", None) or "제목 없음",
                        "source": _extract_domain(url),
                        "content": body,
                        "published_at": getattr(item, "published_date", None),
                        "exa_score": round(float(getattr(item, "score", 0) or 0), 4),
                    }
                )

            kept_count = raw_count - skipped_domain - skipped_empty
            print(
                f"[exa_collector] '{query[:24]}...' API {raw_count}건 -> "
                f"도메인제외 {skipped_domain}, 본문없음 {skipped_empty}, 반영 {kept_count}"
            )
        except Exception as error:
            print(f"[exa_collector] 쿼리 실패 ({query[:20]}...): {error}")

    deduped_results: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for row in results:
        url = str(row["url"])
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped_results.append(row)

    print(f"[exa_collector] 수집 완료: {len(deduped_results)}건 (원본 {len(results)}건)")
    return deduped_results

