"""
Summary:
Core debate orchestration:
- 4 role agents produce opening statements
- 4 role agents critique the packet
- Judge synthesizes a final decision
Outputs a structured DebateResult dict + trace for debugging.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable

from agent_debate.prompts import ROLE_SYSTEM_PROMPTS
from agent_debate.jsonutil import call_llm_json

AGENTS = ["Optimist", "Skeptic", "Operator", "LongTerm"]

@dataclass
class DebateState:
    """
    Summary:
    Holds the full debate artifact so you can print it, store it, or render it later.
    """
    question: str
    context: str = ""
    openings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    critiques: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    verdict: Dict[str, Any] = field(default_factory=dict)
    trace: List[Dict[str, Any]] = field(default_factory=list)


def run_debate(
    *,
    question: str,
    context: str,
    llm_call_fn: Callable[..., str],
) -> DebateState:
    """
    Summary:
    Runs the end-to-end debate and returns a DebateState.
    llm_call_fn must accept (system_prompt=..., user_prompt=...) and return text.
    """
    state = DebateState(question=question, context=context)

    # Round 0: Openings
    for role in AGENTS:
        sys = ROLE_SYSTEM_PROMPTS[role]
        user = f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"
        out = call_llm_json(llm_call_fn, system_prompt=sys, user_prompt=user)
        state.openings[role] = out
        state.trace.append({"phase": "opening", "role": role, "output": out})

    # Round 1: Critiques (everyone sees everyone's openings)
    openings_packet = json.dumps(state.openings, indent=2)
    for role in AGENTS:
        sys = ROLE_SYSTEM_PROMPTS[role]
        user = (
            f"QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\n"
            f"OTHER AGENTS' OPENINGS (JSON):\n{openings_packet}\n\n"
            "Now critique the other agents. Focus on gaps, weak assumptions, and missing options.\n"
            "Return ONLY your role's JSON schema."
        )
        out = call_llm_json(llm_call_fn, system_prompt=sys, user_prompt=user)
        state.critiques[role] = out
        state.trace.append({"phase": "critique", "role": role, "output": out})

    # Final: Judge verdict
    judge_sys = ROLE_SYSTEM_PROMPTS["Judge"]
    packet = json.dumps({"openings": state.openings, "critiques": state.critiques}, indent=2)
    judge_user = f"QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\nDEBATE PACKET (JSON):\n{packet}"
    verdict = call_llm_json(llm_call_fn, system_prompt=judge_sys, user_prompt=judge_user)
    state.verdict = verdict
    state.trace.append({"phase": "verdict", "role": "Judge", "output": verdict})

    return state
