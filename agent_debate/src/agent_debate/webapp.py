"""
Summary:
FastAPI web app:
- GET / serves a simple HTML UI
- POST /api/debate runs the debate and returns JSON
"""

from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from agent_debate.runner import run_debate
from agent_debate.llm_router import get_llm_call_fn


APP_DIR = Path(__file__).resolve().parent
INDEX_HTML = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")

app = FastAPI()


class DebateRequest(BaseModel):
    question: str
    context: str = ""
    provider: str = "openai"  # "ollama" or "openai"
    openai_model: str | None = None
    ollama_model: str | None = None
    ollama_base_url: str | None = None
    ollama_timeout: int = 180


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.post("/api/debate")
def api_debate(req: DebateRequest) -> JSONResponse:
    # Build the LLM function based on provider (hybrid)
    llm_call_fn = get_llm_call_fn(
        provider=req.provider,
        ollama_model=req.ollama_model,
        ollama_base_url=req.ollama_base_url,
        ollama_timeout_s=req.ollama_timeout,
        openai_model=req.openai_model,
        openai_timeout_s=None,
    )

    state = run_debate(
        question=req.question.strip(),
        context=req.context.strip(),
        llm_call_fn=llm_call_fn,
    )

    # Return a clean JSON payload for the UI
    return JSONResponse(
        {
            "question": state.question,
            "context": state.context,
            "openings": state.openings,
            "critiques": state.critiques,
            "verdict": state.verdict,
            "trace": state.trace,
        }
    )
