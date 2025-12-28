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
        task_id = action.get("id")
        if task_id:
            ok = mark_done(int(task_id))
            return f"Marked done ✅ (id={task_id})" if ok else "That task was already done."
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
    Summary: Intercepts delete-task and mark-done requests and returns an action dict
    grounded in real DB tasks (by id). Returns None if it should fall back to LLM.
    """

    # -----------------------------
    # MARK DONE / COMPLETE TASK
    # -----------------------------
    # Examples it should catch:
    # - "Set DD batteries task to be done"
    # - "Mark Buy DD batteries done"
    # - "Complete task #9"
    # - "Done #9"
    mark_done_trigger = (
        re.search(r"\b(mark|set|complete|finish|done)\b", user_text, re.I)
        and re.search(r"\b(done|complete|completed|finished)\b|\bto be done\b", user_text, re.I)
    ) or re.search(r"\b(done|complete)\s*#\d+\b", user_text, re.I)

    if mark_done_trigger:
        tasks = list_tasks(status="open")

        # If user mentions an id like "#9" or "id 9", use it directly
        m_id = re.search(r"(?:#|id\s*)(\d+)\b", user_text, re.I)
        if m_id:
            task_id = int(m_id.group(1))
            return {
                "intent": "mark_done",
                "id": task_id,
                "title": "",
                "due": "",
                "notify": ["cli"],
                "notes": "",
                "questions": [],
            }

        # Heuristic: extract a title fragment from the text
        # "Set DD batteries task to be done" -> "DD batteries"
        frag = user_text

        # Remove common command words
        frag = re.sub(r"(?i)\b(set|mark|complete|finish)\b", "", frag)
        # Remove "task ..." tail
        frag = re.sub(r"(?i)\btask\b.*$", "", frag)
        # Remove "to be done" tail
        frag = re.sub(r"(?i)\bto be done\b", "", frag)
        # Remove done/complete tokens
        frag = re.sub(r"(?i)\b(done|complete|completed|finished)\b", "", frag)

        frag = frag.strip().strip("'\"")

        candidates = tasks
        if frag:
            f = frag.lower()
            candidates = [t for t in tasks if f in (t.get("title") or "").lower()]

        if len(candidates) == 1:
            return {
                "intent": "mark_done",
                "id": candidates[0]["id"],
                "title": "",
                "due": "",
                "notify": ["cli"],
                "notes": "",
                "questions": [],
            }

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
                    "Which task id should I mark done? Reply like: done #9",
                    "Here are the closest matches:\n" + "\n".join(options),
                ],
            }

        return {
            "intent": "clarify",
            "title": "",
            "due": "",
            "notify": ["cli"],
            "notes": "",
            "questions": ["I couldn't find a matching open task. What’s the exact task title or id (e.g., #9)?"],
        }

    # -----------------------------
    # DELETE TASK (your existing code)
    # -----------------------------
    delete_trigger = (
            re.search(r"\b(delete|remove|cancel|trash)\b", user_text, re.I) 
            and (
                re.search(r"\btask\b", user_text, re.I) 
                or re.search(r"(?:#|id\s*)\d+", user_text, re.I)
            )
        )

    if not delete_trigger:
        return None

    tasks = list_tasks(status="open")

    # 1. Check for explicit ID match (Highest Priority)
    m_id = re.search(r"(?:#|id\s*)(\d+)\b", user_text, re.I)
    if m_id:
        task_id = int(m_id.group(1))
        return {
            "intent": "delete_task",
            "id": task_id,
            "title": "",
            "due": "",
            "notify": ["cli"],
            "notes": "",
            "questions": []
        }

    # 2. Heuristic: Extract title fragment
    frag = user_text
    # Remove command words
    frag = re.sub(r"(?i)\b(delete|remove|cancel|trash)\b", "", frag)
    # Remove "task"
    frag = re.sub(r"(?i)\btask\b", "", frag)
    # Clean up whitespace/quotes
    frag = frag.strip().strip("'\"")

    candidates = tasks

    # 3. Filter candidates
    # Special case: "Delete tasks with no due date"
    if re.search(r"\bno due\b|\bno due date\b|\bwithout (a )?(date|due)\b", user_text, re.I):
        candidates = [t for t in tasks if not t.get("due")]
    elif frag:
        # Filter by title fragment
        f = frag.lower()
        candidates = [t for t in tasks if f in (t.get("title") or "").lower()]

    # 4. Determine Action based on matches
    if len(candidates) == 1:
        return {
            "intent": "delete_task",
            "id": candidates[0]["id"],
            "title": "",
            "due": "",
            "notify": ["cli"],
            "notes": "",
            "questions": []
        }

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

    return {
        "intent": "clarify",
        "title": "",
        "due": "",
        "notify": ["cli"],
        "notes": "",
        "questions": ["I couldn't find a matching open task to delete. What’s the exact task title or id?"],
    }
