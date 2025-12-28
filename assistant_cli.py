import json
import re
import requests
from datetime import datetime
from assistant.db import init_db
from assistant.tasks import create_task, list_tasks, mark_done, find_open_by_title_fragment

MODEL = "llama3.2"  # <-- MUST match `ollama list` exactly
CHAT_URL = "http://localhost:11434/api/chat"

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


def call_ollama(user_text: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
    }
    r = requests.post(CHAT_URL, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"]

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

def execute_action(action: dict) -> str:
    intent = action.get("intent", "unknown")
    title = (action.get("title") or "").strip()
    due = (action.get("due") or "").strip()
    notes = (action.get("notes") or "").strip()

    if intent in {"create_task", "create_reminder"}:
        if not title:
            return "I need a title to save that. Try: 'Add a task: ...'"
        task_id = create_task(intent=intent, title=title, due=due, notes=notes)
        return f"Created ✅ (id={task_id})"

    if intent == "list_tasks":
        rows = list_tasks(status="open")
        if not rows:
            return "No open tasks ✅"
        lines = []
        for r in rows:
            due_txt = f" (due {r['due']})" if r["due"] else ""
            lines.append(f"- #{r['id']} {r['title']}{due_txt}")
        return "Open tasks:\n" + "\n".join(lines)

    if intent == "mark_done":
        # simplest: if title provided, find by fragment; else ask user for id later (Phase 2.1)
        if title:
            matches = find_open_by_title_fragment(title)
            if not matches:
                return f"Couldn't find an open task matching '{title}'."
            task_id = matches[0]["id"]
            ok = mark_done(task_id)
            return f"Marked done ✅ (id={task_id})" if ok else "That task was already done."
        return "Tell me which task to mark done (e.g., 'Mark task 3 done')."

    if intent == "clarify":
        qs = action.get("questions", [])
        if qs:
            return "I need one more thing:\n- " + "\n- ".join(qs)
        return "I need a bit more info."

    return "I’m not sure how to do that yet."

def main() -> None:
    init_db()
    print("AI Daily Assistant — Phase 1 (Task-first JSON)")
    print("Type a request. Type 'quit' to exit.\n")

    while True:
        user = input("You> ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        if not user:
            continue

        try:
            raw = call_ollama(user)
            action, friendly = split_json_and_message(raw)

            print("\nAction JSON>")
            print(json.dumps(action, ensure_ascii=False))

            print("\nAssistant>")
            print(friendly if friendly else "(No message returned)")
            print()

            result = execute_action(action)
            print("System>")
            print(result)
            print()

        except Exception as e:
            print(f"\n[error] {type(e).__name__}: {e}\n")

if __name__ == "__main__":
    main()
