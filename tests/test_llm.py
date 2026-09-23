"""LLM provider configuration."""

import os
from unittest.mock import patch

from src.llm import (
    _openrouter_reasoning_kwargs,
    get_max_tokens,
    get_model,
    get_provider,
    llm_is_configured,
)


def test_openrouter_configured():
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-x"}, clear=True):
        assert get_provider() == "openrouter"
        assert llm_is_configured()
        assert get_model() == "google/gemma-4-31b-it"


def test_not_configured_without_key():
    with patch.dict(os.environ, {}, clear=True):
        assert get_provider() is None
        assert not llm_is_configured()


def test_llm_max_tokens_default_and_override():
    with patch.dict(os.environ, {}, clear=True):
        assert get_max_tokens() == 8192
    with patch.dict(os.environ, {"LLM_MAX_TOKENS": "12000"}, clear=True):
        assert get_max_tokens() == 12000


def test_reasoning_kwargs_only_when_configured():
    with patch.dict(os.environ, {}, clear=True):
        assert _openrouter_reasoning_kwargs() == {}
    with patch.dict(os.environ, {"LLM_REASONING_EFFORT": "low"}, clear=True):
        assert _openrouter_reasoning_kwargs() == {"reasoning_effort": "low"}


def test_llm_model_override():
    with patch.dict(
        os.environ,
        {"OPENROUTER_API_KEY": "o", "LLM_MODEL": "anthropic/claude-sonnet-4"},
        clear=True,
    ):
        assert get_model() == "anthropic/claude-sonnet-4"
