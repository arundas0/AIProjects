"""
Summary:
LLM router for hybrid usage:
- provider="openai" -> always OpenAI
- provider="ollama" -> always Ollama
- provider="hybrid" (or env LLM_PROVIDER=hybrid) -> try Ollama, fallback to OpenAI on error

Returned callable signature:
  fn(system_prompt=..., user_prompt=...) -> str
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from agent_debate.llm_ollama import ollama_chat, LLMError as OllamaError
from agent_debate.llm_openai import openai_chat, LLMError as OpenAIError


def get_llm_call_fn(
    *,
    provider: Optional[str],
    ollama_model: Optional[str],
    ollama_base_url: Optional[str],
    ollama_timeout_s: int,
    openai_model: Optional[str],
    openai_timeout_s: Optional[float],
) -> Callable[..., str]:
    """
    Summary:
    Build a function with signature:
      fn(system_prompt=..., user_prompt=...) -> str

    Provider resolution order:
    1) explicit `provider` argument if non-empty
    2) env var LLM_PROVIDER
    3) default "ollama"

    Supported values:
    - "ollama"
    - "openai"
    - "hybrid" (try Ollama, fallback to OpenAI)
    """
    chosen = (provider or os.getenv("LLM_PROVIDER") or "ollama").strip().lower()

    def call_openai(*, system_prompt: str, user_prompt: str) -> str:
        return openai_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=openai_model
        )

    def call_ollama(*, system_prompt: str, user_prompt: str) -> str:
        return ollama_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=ollama_model,
            base_url=ollama_base_url,
            timeout_s=ollama_timeout_s,
        )

    if chosen == "openai":
        return call_openai

    if chosen == "ollama":
        return call_ollama

    if chosen == "hybrid":
        # Try Ollama first; if it fails (timeout/connection), fall back to OpenAI.
        def call_hybrid(*, system_prompt: str, user_prompt: str) -> str:
            try:
                return call_ollama(system_prompt=system_prompt, user_prompt=user_prompt)
            except (OllamaError, Exception):
                return call_openai(system_prompt=system_prompt, user_prompt=user_prompt)

        return call_hybrid

    raise ValueError(f"Unknown provider '{chosen}'. Expected one of: ollama, openai, hybrid.")
