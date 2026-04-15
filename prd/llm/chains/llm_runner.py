"""LLM chain execution: model creation, invocation, and retry logic."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from prd.config import get_gemini_api_key, get_gemini_model
from prd.llm.chains.category_registry import get_allowed_categories
from prd.llm.prompts.causal_prompt import build_causal_prompt
from prd.llm.prompts.repair_prompt import REPAIR_PROMPT
from prd.llm.prompts.summary_prompt import SUMMARY_PROMPT

MAX_MODEL_RETRIES = 3
RETRYABLE_ERROR_MARKERS = (
    "429",
    "quota",
    "resource exhausted",
    "deadline exceeded",
    "temporarily unavailable",
    "service unavailable",
    "internal",
    "timeout",
    "connection reset",
)


def _create_model(*, temperature: float, max_tokens: int) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=get_gemini_model(),
        google_api_key=get_gemini_api_key(),
        temperature=temperature,
        max_output_tokens=max_tokens,
    )


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "\n".join(part.strip() for part in parts if part).strip()
    return str(content).strip()


def _print_chain_response(label: str, text: str) -> None:
    print(f"[{label}] --- RESPONSE START ---")
    print(text)
    print(f"[{label}] --- RESPONSE END ---")


def _print_chain_prompt(label: str, prompt: Any, payload: dict[str, Any]) -> None:
    try:
        messages = prompt.format_messages(**payload)
    except Exception:
        return

    for message in messages:
        role = getattr(message, "type", "message").upper()
        text = _message_text(message)
        print(f"[{label}] --- {role} PROMPT START ---")
        print(text)
        print(f"[{label}] --- {role} PROMPT END ---")


def _is_retryable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in RETRYABLE_ERROR_MARKERS)


async def _invoke_chain(
    prompt: Any,
    payload: dict[str, Any],
    *,
    temperature: float,
    max_tokens: int,
) -> str:
    chain = prompt | _create_model(temperature=temperature, max_tokens=max_tokens)
    last_error: Exception | None = None

    for attempt in range(1, MAX_MODEL_RETRIES + 1):
        try:
            response = await chain.ainvoke(payload)
            return _message_text(response)
        except Exception as exc:
            last_error = exc
            if attempt >= MAX_MODEL_RETRIES or not _is_retryable_error(exc):
                raise
            await asyncio.sleep(0.8 * attempt)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Chain invocation failed without a captured exception.")


async def run_summary_chain(content: str) -> str:
    payload = {"content": content[:4000]}
    _print_chain_prompt("LLM1", SUMMARY_PROMPT, payload)
    text = await _invoke_chain(
        SUMMARY_PROMPT,
        payload,
        temperature=0.2,
        max_tokens=1536,
    )
    if not text:
        raise ValueError("Summary chain returned an empty response.")
    _print_chain_response("LLM1", text)
    return text


async def run_causal_chain(
    summary: str,
    history_context: str = "없음",
    categories: list[dict] | None = None,
    indicator_context: str = "데이터 없음",
) -> str:
    allowed_categories = categories or list(get_allowed_categories())
    text = await _invoke_chain(
        build_causal_prompt(allowed_categories),
        {"summary": summary, "history_context": history_context, "indicator_context": indicator_context},
        temperature=0.15,
        max_tokens=8192,
    )
    if not text:
        raise ValueError("Causal chain returned an empty response.")
    _print_chain_response("LLM2", text)
    return text


async def run_repair_chain(summary: str, causal_raw: str) -> str:
    text = await _invoke_chain(
        REPAIR_PROMPT,
        {"summary": summary, "causal_raw": causal_raw[:4000]},
        temperature=0.1,
        max_tokens=8192,
    )
    if not text:
        raise ValueError("Repair chain returned an empty response.")
    _print_chain_response("LLM3", text)
    return text
