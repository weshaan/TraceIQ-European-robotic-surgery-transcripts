"""LLM wrapper — OpenRouter via LangChain ChatOpenAI (OpenAI-compatible API)."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any, Callable, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import BadRequestError, LengthFinishReasonError, RateLimitError

Provider = Literal["openrouter"]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "google/gemma-4-31b-it"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 8192
MAX_TOKENS_RETRY_CAP = 32768

_thread_local = threading.local()


def get_openrouter_api_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY")


def get_provider() -> Provider | None:
    return "openrouter" if get_openrouter_api_key() else None


def llm_is_configured() -> bool:
    return bool(get_openrouter_api_key())


def get_model() -> str:
    if os.environ.get("LLM_MODEL"):
        return os.environ["LLM_MODEL"].strip()
    return (os.environ.get("OPENROUTER_MODEL") or "").strip() or DEFAULT_MODEL


def get_max_tokens() -> int:
    raw = (os.environ.get("LLM_MAX_TOKENS") or "").strip()
    if not raw:
        return DEFAULT_MAX_TOKENS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_TOKENS
    return max(256, min(value, MAX_TOKENS_RETRY_CAP))


def get_reasoning_effort() -> str | None:
    """Optional reasoning-model effort: none, low, medium, high, etc."""
    raw = (os.environ.get("LLM_REASONING_EFFORT") or "").strip().lower()
    return raw or None


def _openrouter_use_strict_json() -> bool:
    raw = (os.environ.get("LLM_STRICT_JSON") or "").strip().lower()
    return raw in ("1", "true", "yes")


def _openrouter_reasoning_kwargs(explicit_effort: str | None = None) -> dict[str, Any]:
    effort = explicit_effort if explicit_effort is not None else get_reasoning_effort()
    if effort:
        return {"reasoning_effort": effort}
    return {}


def _reasoning_mandatory_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "reasoning is mandatory" in msg or "cannot be disabled" in msg


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("LLM response did not contain valid JSON")


def _response_text(result: Any) -> str:
    extra = getattr(result, "additional_kwargs", None) or {}
    parsed = extra.get("parsed")
    if isinstance(parsed, dict):
        return json.dumps(parsed)
    if parsed is not None:
        return str(parsed)

    content = getattr(result, "content", result)
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type")
                if block_type in ("text", "output_text"):
                    parts.append(str(block.get("text", "")))
                elif block_type in ("reasoning", "thinking", "reasoning_content"):
                    continue
                elif "text" in block:
                    parts.append(str(block.get("text", "")))
            elif hasattr(block, "text"):
                parts.append(str(block.text))
        text = "".join(parts)
    else:
        text = str(content)

    if text.strip():
        return text

    for key in ("reasoning_content", "reasoning"):
        alt = extra.get(key)
        if isinstance(alt, str) and alt.strip():
            text = alt
            break

    return text


def _finish_reason(result: Any) -> str | None:
    meta = getattr(result, "response_metadata", None) or {}
    reason = meta.get("finish_reason")
    if reason:
        return str(reason)
    info = getattr(result, "generation_info", None) or {}
    reason = info.get("finish_reason")
    return str(reason) if reason else None


def _rate_limit_message(exc: Exception) -> str:
    body = str(exc)
    if "rate-limited" in body.lower() or ":free" in body:
        return (
            "OpenRouter rate limit on the free/shared pool for this model. "
            "Wait and retry, pick a non-:free model, or add a provider key at "
            "https://openrouter.ai/settings/integrations"
        )
    return (
        "OpenRouter rate limit (429). Wait a moment and retry, or switch LLM_MODEL."
    )


def _call_with_json_retry(get_text: Callable[[], str], retry: Callable[[str], str]) -> dict[str, Any]:
    raw = get_text()
    try:
        return _extract_json(raw)
    except ValueError:
        raw2 = retry(raw)
        return _extract_json(raw2)


def _openrouter_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    referer = os.environ.get("OPENROUTER_HTTP_REFERER")
    title = os.environ.get("OPENROUTER_APP_TITLE", "hasamex-transcript-app")
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title
    return headers


def _build_openrouter_chat(
    *,
    model: str,
    temperature: float,
    api_key: str,
    max_tokens: int,
    reasoning_effort: str | None = None,
) -> ChatOpenAI:
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "api_key": api_key,
        "base_url": OPENROUTER_BASE_URL,
        "default_headers": _openrouter_headers() or None,
        **_openrouter_reasoning_kwargs(reasoning_effort),
    }
    if _openrouter_use_strict_json():
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
    return ChatOpenAI(**kwargs)


def _require_api_key() -> str:
    api_key = get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. See .env.example.")
    return api_key


def _get_thread_chat(model: str, temperature: float, max_tokens: int) -> Any:
    bucket: dict[tuple[str, float, int, str], Any] | None = getattr(
        _thread_local, "chats", None
    )
    if bucket is None:
        bucket = {}
        _thread_local.chats = bucket
    effort_key = get_reasoning_effort() or ""
    key = (model, temperature, max_tokens, effort_key)
    if key in bucket:
        return bucket[key]
    bucket[key] = _build_openrouter_chat(
        model=model,
        temperature=temperature,
        api_key=_require_api_key(),
        max_tokens=max_tokens,
    )
    return bucket[key]


def _invoke_json_chat(
    chat: Any,
    system: str,
    user: str,
    *,
    client_factory: Callable[[], Any] | None,
    max_tokens: int,
    rebuild_chat: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    if client_factory:
        chat = client_factory()

    def _invoke_once(active: Any, prompt: str) -> Any:
        last_rate_exc: RateLimitError | None = None
        for attempt in range(4):
            try:
                return active.invoke(
                    [SystemMessage(content=system), HumanMessage(content=prompt)]
                )
            except LengthFinishReasonError:
                raise
            except RateLimitError as exc:
                last_rate_exc = exc
                if attempt >= 3:
                    raise RuntimeError(_rate_limit_message(exc)) from exc
                time.sleep(2**attempt)
        assert last_rate_exc is not None
        raise RuntimeError(_rate_limit_message(last_rate_exc)) from last_rate_exc

    def generate(
        prompt: str,
        token_limit: int | None = None,
        *,
        reasoning_effort: str | None = None,
    ) -> str:
        limit = token_limit or max_tokens
        active = chat
        if rebuild_chat is not None and (
            token_limit is not None or reasoning_effort is not None
        ):
            active = rebuild_chat(limit, reasoning_effort)
        try:
            result = _invoke_once(active, prompt)
        except BadRequestError as exc:
            if (
                _reasoning_mandatory_error(exc)
                and rebuild_chat is not None
                and reasoning_effort != "low"
            ):
                return generate(
                    prompt, token_limit, reasoning_effort="low"
                )
            raise
        except LengthFinishReasonError as exc:
            bumped = min(max(limit, max_tokens) * 2, MAX_TOKENS_RETRY_CAP)
            if rebuild_chat is not None and bumped > limit:
                return generate(prompt, bumped)
            raise RuntimeError(
                "The model hit the output token limit before finishing JSON. "
                f"Current limit: {limit}. "
                "Set LLM_MAX_TOKENS higher in .env (e.g. 16384), use a non-reasoning model, "
                "or set LLM_REASONING_EFFORT=low for reasoning-only models."
            ) from exc
        text = _response_text(result)
        if not text.strip():
            reason = _finish_reason(result)
            if reason == "length" and rebuild_chat is not None:
                bumped = min(max(limit, max_tokens) * 2, MAX_TOKENS_RETRY_CAP)
                if bumped > limit:
                    return generate(prompt, bumped)
            raise ValueError(
                "Empty response from LLM (often reasoning models using the full token budget). "
                "Try LLM_REASONING_EFFORT=low, LLM_MAX_TOKENS=16384, or a non-reasoning model."
            )
        if _finish_reason(result) == "length" and rebuild_chat is not None:
            bumped = min(max(limit, max_tokens) * 2, MAX_TOKENS_RETRY_CAP)
            if bumped > limit:
                try:
                    _extract_json(text)
                except ValueError:
                    return generate(prompt, bumped)
        return text

    return _call_with_json_retry(
        lambda: generate(user),
        lambda raw: generate(
            f"{user}\n\nYour previous reply was not valid JSON:\n{raw}\n\n"
            "Reply with a single JSON object only."
        ),
    )


def call_llm(
    system: str,
    user: str,
    *,
    temperature: float = DEFAULT_TEMPERATURE,
    model: str | None = None,
    client_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """
    Call OpenRouter and parse a JSON object from the response.
    client_factory: for tests — mock with .invoke() returning .content text.
    """
    if not llm_is_configured() and client_factory is None:
        raise RuntimeError(
            "No LLM configured. Set OPENROUTER_API_KEY in .env. See .env.example."
        )
    model = model or get_model()
    max_tokens = get_max_tokens()
    chat = (
        _get_thread_chat(model, temperature, max_tokens)
        if client_factory is None
        else None
    )
    rebuild = (
        None
        if client_factory is not None
        else lambda limit, reasoning_effort=None: _build_openrouter_chat(
            model=model,
            temperature=temperature,
            api_key=_require_api_key(),
            max_tokens=limit,
            reasoning_effort=reasoning_effort,
        )
    )
    return _invoke_json_chat(
        chat,
        system,
        user,
        client_factory=client_factory,
        max_tokens=max_tokens,
        rebuild_chat=rebuild,
    )
