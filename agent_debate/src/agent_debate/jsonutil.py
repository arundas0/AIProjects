"""
Summary:
Utilities for parsing model output as JSON with one retry for "JSON repair".
This keeps the orchestration code simple and robust.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Callable


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Summary:
    Best-effort JSON parse. Returns dict if valid JSON object, else None.
    """
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def call_llm_json(
    llm_call_fn: Callable[..., str],
    *,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 1,
) -> Dict[str, Any]:
    """
    Summary:
    Calls an LLM function that returns text, and forces a dict JSON output.
    Retries once with a "return ONLY valid JSON" repair prompt if needed.
    """
    raw = llm_call_fn(system_prompt=system_prompt, user_prompt=user_prompt)
    parsed = _try_parse_json(raw)
    if parsed is not None:
        return parsed

    if max_retries > 0:
        repair_prompt = (
            "Your previous response was not valid JSON.\n"
            "Return ONLY valid JSON (no markdown, no commentary).\n"
            "Do not wrap in backticks.\n\n"
            f"Previous output:\n{raw}"
        )
        raw2 = llm_call_fn(system_prompt=system_prompt, user_prompt=repair_prompt)
        parsed2 = _try_parse_json(raw2)
        if parsed2 is not None:
            return parsed2

        return {"error": "invalid_json_after_retry", "raw": raw2, "previous_raw": raw}

    return {"error": "invalid_json", "raw": raw}
