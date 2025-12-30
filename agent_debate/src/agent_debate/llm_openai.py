"""
Summary:
Adapter for calling OpenAI Chat Completions. Returns assistant text content.
Keeps OpenAI-specific code isolated from debate orchestration.
"""

from __future__ import annotations
import os
from openai import OpenAI


class LLMError(Exception):
    """Raised when the OpenAI call fails."""


_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def openai_chat(*, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    """
    Summary:
    Calls OpenAI and returns assistant message content as a string.
    """
    model = model or os.getenv("OPENAI_MODEL", "gpt-5.2")
    print(f"Calling OpenAI model={model}...")
    try:

        resp = _client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt + "\n\nReturn ONLY valid JSON."},
                {"role": "user", "content": user_prompt},
            ],
        )
        print("OpenAI call successful.",resp.choices[0].message.content.strip())
        return resp.choices[0].message.content.strip()

    except Exception as e:
        raise LLMError(f"OpenAI call failed: {e}") from e
