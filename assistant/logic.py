from assistant.tasks import create_task, list_tasks, mark_done, find_open_by_title_fragment, delete_task
import re

def execute_action(action: dict) -> str:
    """
    Takes the model-produced action JSON and performs it using SQLite-backed functions.
    Returns a human-readable 'system result' string for UI display.
    """
    intent = action.get("intent", "unknown")
    title = (action.get("title") or "").strip()
    due = (action.get("due") or "").strip()
    notes = (action.get("notes") or "").strip()

    if intent in {"create_task", "create_reminder"}:
        if not title:
            return "I need a title to save that."
        task_id = create_task(intent=intent, title=title, due=due, notes=notes)
        return f"Saved ✅ (id={task_id})"

    if intent == "list_tasks":
        rows = list_tasks(status="open")
        if not rows:
            return "No open tasks ✅"
        lines = []
        for r in rows:
            due_txt = f" (due {r['due']})" if r["due"] else ""
            lines.append(f"- #{r['id']} {r['title']}{due_txt}")
        return "Open tasks:\n" + "\n".join(lines)

    if intent == "delete_task":
        task_id = action.get("id")
        if task_id:
            ok = delete_task(int(task_id))
            return f"Deleted ✅ (id={task_id})" if ok else "Failed to delete." 
        if title:
            matches = find_open_by_title_fragment(title)
            if not matches:
                return f"Couldn't find an open task matching '{title}'."
            task_id = matches[0]["id"]
            ok = delete_task(task_id)
            return f"Deleted ✅ (id={task_id})" if ok else "Failed to delete."
        return "Tell me which task to delete."

    if intent == "mark_done":
        if title:
            matches = find_open_by_title_fragment(title)
            if not matches:
                return f"Couldn't find an open task matching '{title}'."
            task_id = matches[0]["id"]
            ok = mark_done(task_id)
            return f"Marked done ✅ (id={task_id})" if ok else "That task was already done."
        return "Tell me which task to mark done."

    if intent == "clarify":
        qs = action.get("questions", [])
        if qs:
            return "I need:\n- " + "\n- ".join(qs)
        return "I need more info."

    return "I’m not sure how to do that yet."


def route_user_text(user_text: str) -> dict | None:
    """
    Summary: Intercepts delete-task requests and returns an action dict
    without calling the LLM. Returns None if it should fall back to LLM.
    """

    # Detect delete/remove/trash + task
    if not (re.search(r"\b(delete|remove|trash)\b", user_text, re.I) and re.search(r"\btask\b", user_text, re.I)):
        return None

    tasks = list_tasks(status="open")

    # If user said "no due date", prefer due==None/""
    if re.search(r"\bno due\b|\bno due date\b|\bwithout (a )?(date|due)\b", user_text, re.I):
        candidates = [t for t in tasks if not t.get("due")]
    else:
        candidates = tasks

    # If user mentions an id like "#7" or "id 7", use it directly
    m_id = re.search(r"(?:#|id\s*)(\d+)\b", user_text, re.I)
    if m_id:
        task_id = int(m_id.group(1))
        return {"intent": "delete_task", "id": task_id, "title": "", "due": "", "notify": ["cli"], "notes": "", "questions": []}

    # If exactly one candidate, delete by id (preferred) but we’ll pass title fallback too
    if len(candidates) == 1:
        return {"intent": "delete_task", "id": candidates[0]["id"], "title": "", "due": "", "notify": ["cli"], "notes": "", "questions": []}

    # If ambiguous, ask a specific question and show options
    if len(candidates) > 1:
        options = []
        for t in candidates[:10]:
            due_txt = f"(due {t['due']})" if t.get("due") else "(no due date)"
            options.append(f"#{t['id']} {t['title']} {due_txt}")

        return {
            "intent": "clarify",
            "title": "",
            "due": "",
            "notify": ["cli"],
            "notes": "",
            "questions": [
                "Which task id should I delete? Reply like: delete #7",
                "Here are the closest matches:\n" + "\n".join(options),
            ],
        }

    # No matches
    return {
        "intent": "clarify",
        "title": "",
        "due": "",
        "notify": ["cli"],
        "notes": "",
        "questions": ["I couldn't find any matching open tasks. What’s the exact task title?"],
    }
