"""
Summary:
A small adapter for calling a local Ollama model via the /api/chat endpoint.
Keeps model + HTTP details isolated from the debate orchestration code.
"""

from __future__ import annotations

import os
import requests


class LLMError(Exception):
    """Summary: Raised when the LLM call fails (network/API/model issues)."""


def ollama_chat(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 60,
) -> str:
    """
    Summary:
    Calls Ollama /api/chat with a system+user message and returns assistant content as text.

    Notes:
    - We also append "Return ONLY valid JSON." to the system prompt to reduce formatting drift.
    - model defaults to $OLLAMA_MODEL or "llama3.2".
    - base_url defaults to $OLLAMA_URL or "http://localhost:11434".
    """
    model = model or os.getenv("OLLAMA_MODEL", "llama3.2:latest")
    base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    chat_url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt.strip() + "\n\nReturn ONLY valid JSON."},
            {"role": "user", "content": user_prompt.strip()},
        ],
    }

    try:
        r = requests.post(chat_url, json=payload, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise LLMError(f"Ollama call failed: {e}") from e

    msg = data.get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content:
        raise LLMError(f"Ollama returned empty content. Top-level keys: {list(data.keys())}")
    return content
