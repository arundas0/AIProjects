from assistant.tasks import create_task, list_tasks, mark_done, find_open_by_title_fragment

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
