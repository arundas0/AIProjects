"""
Summary:
CLI entrypoint so you can run:
  PYTHONPATH=src python -m agent_debate "question" --context "..."
Prints openings, critiques, and final verdict.
"""

from __future__ import annotations

import argparse
import json

from agent_debate.llm_ollama import ollama_chat
from agent_debate.runner import run_debate
from agent_debate.llm_openai import openai_chat

def main() -> None:
    parser = argparse.ArgumentParser(prog="agent_debate", description="Multi-agent debate runner (local Ollama).")
    parser.add_argument("question", type=str, help="The decision/question to debate.")
    parser.add_argument("--context", type=str, default="", help="Optional extra context.")
    parser.add_argument("--model", type=str, default=None, help="Ollama model name (overrides OLLAMA_MODEL).")
    parser.add_argument("--base-url", type=str, default=None, help="Ollama base URL (overrides OLLAMA_URL).")
    parser.add_argument("--timeout", type=int, default=300, help="HTTP timeout in seconds for Ollama calls.")
    parser.add_argument("--provider", type=str, default="openai", help="Default to OpenAI or Ollama LLM provider.")
    
    args = parser.parse_args()

    def llm_call_fn(*, system_prompt: str, user_prompt: str) -> str:
        if(args.provider.lower() == "ollama"):
            return ollama_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=args.model,
                base_url=args.base_url,
                timeout_s=args.timeout,)
        else: 
            return openai_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=args.model,)
        
    _ = llm_call_fn(system_prompt="Return ONLY valid JSON.", user_prompt='{"warmup":true}')
    
    state = run_debate(question=args.question, context=args.context, llm_call_fn=llm_call_fn)

    print("\n=== OPENINGS ===")
    for role, out in state.openings.items():
        print(f"\n[{role}]")
        print(json.dumps(out, indent=2))

    print("\n=== CRITIQUES ===")
    for role, out in state.critiques.items():
        print(f"\n[{role}]")
        print(json.dumps(out, indent=2))

    print("\n=== VERDICT ===")
    print(json.dumps(state.verdict, indent=2))


if __name__ == "__main__":
    main()
