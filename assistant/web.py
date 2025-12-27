import os
import json
import requests
import tempfile
import subprocess
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import UploadFile, File
from assistant.speech import transcribe_wav_file

from assistant.db import init_db
from assistant.tasks import list_tasks
from assistant.logic import execute_action, route_user_text

MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
CHAT_URL = os.environ.get("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")

SYSTEM_PROMPT = """You are a local-first AI Daily Assistant that converts user requests into structured actions.

CRITICAL OUTPUT RULES (must follow exactly):
- Output EXACTLY 2 parts.
- Part 1 must be a valid JSON object. It may be single-line or multi-line. It must appear before any other text.
- The very first character of your entire response must be '{' and the last character of Part 1 must be '}'.
- No markdown, no code fences, no backticks, no extra labels like "JSON:".
- Part 2 must start on the next line after the JSON and be a friendly message (1-2 sentences).

JSON schema (all keys required):
{"intent":"create_reminder"|"create_task"|"list_tasks"|"mark_done"|"clarify"|"unknown",
 "title":string,
 "due":string,
 "notify":string[],
 "notes":string,
 "questions":string[]}

Field rules:
- due must be ISO-8601 datetime if known (e.g. "2026-01-01T09:00:00"), else "".
- Set due ONLY when the user explicitly provides BOTH a date AND a time.
- NEVER invent or assume dates or times.
- notify should default to ["cli"].
- questions must be [] unless intent="clarify".
- If essential info is missing (like date/time for a reminder), set intent="clarify" and ask 1-3 questions.

Decision rules:
- Reminders with time/date -> create_reminder
- General todo items -> create_task
- Asking to see tasks -> list_tasks
- Saying something is completed -> mark_done
- Can't proceed without missing info -> clarify
- Truly unrelated -> unknown

Examples (follow format exactly):

User: Remind me to pay rent
{"intent":"clarify","title":"Pay rent","due":"","notify":["cli"],"notes":"","questions":["What date should I remind you?","What time?"]}
Sure — what date and time should I remind you to pay rent?

User: Remind me to pay rent on Jan 1 at 9am
{"intent":"create_reminder","title":"Pay rent","due":"2026-01-01T09:00:00","notify":["cli"],"notes":"","questions":[]}
Done — I’ll remind you to pay rent on Jan 1 at 9:00 AM.

User: Add a task to buy AA batteries
{"intent":"create_task","title":"Buy AA batteries","due":"","notify":["cli"],"notes":"","questions":[]}
Got it — I added “Buy AA batteries” to your tasks.
"""

def ollama_supports(path: str) -> bool:
    """
    Returns True if Ollama responds with something other than 404 for the given path.
    We use this to select the right endpoint (/api/generate vs /api/chat) reliably.
    """
    try:
        r = requests.get(f"http://localhost:11434{path}", timeout=5)
        return r.status_code != 404
    except Exception:
        return False

def call_ollama(user_text: str) -> str:
    """
    Calls Ollama locally using the classic API.
    Prefers /api/chat if available, otherwise uses /api/generate.
    Returns the assistant text.
    """
    base = "http://localhost:11434"

    # Prefer /api/chat if present
    if ollama_supports("/api/chat"):
        url = f"{base}/api/chat"
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            "stream": False,
        }
        print("[debug] Calling:", url)
        r = requests.post(url, json=payload, timeout=300)
        if not r.ok:
           raise RuntimeError(f"Ollama error {r.status_code} calling {url}: {r.text}")
        r.raise_for_status()
        return r.json()["message"]["content"]

    # Fall back to /api/generate (guaranteed on many installs)
    url = f"{base}/api/generate"
    prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_text}\n"
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    print("[debug] Calling:", url)
    r = requests.post(url, json=payload, timeout=300)
    if not r.ok:
        raise RuntimeError(f"Ollama error {r.status_code} calling {url}: {r.text}")
    r.raise_for_status()
    return r.json().get("response", "")


def extract_first_json_line(text: str) -> dict:
    """
    Extract the first complete JSON object from the model output.
    Works even if JSON is multi-line and followed by a friendly message.
    """
    if not text or not text.strip():
        raise ValueError("Empty model response")

    s = text.lstrip()

    start = s.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in response:\n{text}")

    i = start
    depth = 0
    in_str = False
    escape = False

    while i < len(s):
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    json_blob = s[start:i+1]
                    break
        i += 1
    else:
        raise ValueError(f"Unclosed JSON object in response:\n{text}")

    data = json.loads(json_blob)

    # defaults
    data.setdefault("intent", "unknown")
    data.setdefault("title", "")
    data.setdefault("due", "")
    data.setdefault("notify", ["cli"])
    data.setdefault("notes", "")
    data.setdefault("questions", [])

    if not isinstance(data.get("notify"), list):
        data["notify"] = ["cli"]
    if not isinstance(data.get("questions"), list):
        data["questions"] = []

    return data

def split_json_and_message(text: str) -> tuple[dict, str]:
    s = text.lstrip()
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found")

    # (same brace-balancing loop as above, producing json_blob and end_index)
    i = start
    depth = 0
    in_str = False
    escape = False
    while i < len(s):
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    json_blob = s[start:end]
                    msg = s[end:].strip()
                    return json.loads(json_blob), msg
        i += 1
    raise ValueError("Unclosed JSON object")

def default_friendly_for(action: dict) -> str:
    intent = action.get("intent")

    if intent == "clarify":
        return "Quick question so I delete the right one."

    if intent == "delete_task":
        return "Done — I deleted that task."

    if intent == "mark_done":
        return "All set — I marked it as done."

    return ""

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/tasks")
def api_tasks():
    return JSONResponse({"open": list_tasks(status="open")})

@app.post("/api/ingest")
async def api_ingest(req: Request):
    try:
        body = await req.json()
        user_text = (body.get("text") or "").strip()
        if not user_text:
            return JSONResponse({"error": "Missing text"}, status_code=400)
        routed = route_user_text(user_text)
        if routed is not None:
            action = routed
            friendly = default_friendly_for(action)  # optional; you can synthesize one if you want
        else:
            raw = call_ollama(user_text)
            action, friendly = split_json_and_message(raw)

        system_result = execute_action(action)
        
        if system_result.startswith("Couldn't find") or system_result.startswith("Failed") or system_result.startswith("Tell me"):
            friendly = system_result

        return JSONResponse({
            "action": action,
            "friendly": friendly,
            "system": system_result
        })
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            {"error": f"{type(e).__name__}: {e}"},
            status_code=500
        )
    
@app.post("/api/ingest_audio")
async def api_ingest_audio(audio: UploadFile = File(...)):
    """
    Receives an audio file (WAV recommended), transcribes locally, then
    runs the same pipeline as /api/ingest (LLM -> action -> execute).
    """
    try:
        # Save upload to a temp file
        suffix = ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_in:
            content = await audio.read()
            tmp_in.write(content)
            in_path = tmp_in.name

        out_path = in_path.replace(".webm", ".wav")

        subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, out_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        
        transcript = transcribe_wav_file(out_path)

        if not transcript:
            return JSONResponse({"error": "Could not transcribe audio"}, status_code=400)

        routed = route_user_text(transcript)
        if routed is not None:
            action = routed
            friendly = default_friendly_for(action)  # optional; you can synthesize one if you want
        else:
            raw = call_ollama(transcript)
            action, friendly = split_json_and_message(raw)

        system_result = execute_action(action)
        if system_result.startswith("Couldn't find") or system_result.startswith("Failed") or system_result.startswith("Tell me"):
            friendly = system_result
        
        return JSONResponse({
            "transcript": transcript,
            "action": action,
            "friendly": friendly,
            "system": system_result
        })

    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)
