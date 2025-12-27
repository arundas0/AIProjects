from typing import Any, Dict, List

def build_agent_trace(user_text: str, action: Dict[str, Any], system_result: str, remaining_tasks: int | None = None) -> Dict[str, Any]:
    intent = (action.get("intent") or "").strip()

    decision = intent
    if intent == "delete_task":
        decision = f"delete_task(id={action.get('id')})"
    elif intent == "mark_done":
        decision = f"mark_done(task_id={action.get('task_id') or action.get('id')})"
    elif intent == "create_task":
        decision = f"create_task(title={action.get('title')!r}, due={action.get('due')!r})"
    elif intent == "list_tasks":
        decision = "list_tasks()"

    # Cheap “DB result” classifier based on your current system_result strings
    lower = (system_result or "").lower()
    if "error" in lower or "failed" in lower or "couldn't" in lower:
        db_result = "error"
    elif "deleted" in lower or "removed" in lower or "created" in lower or "done" in lower or "updated" in lower:
        db_result = "success"
    else:
        db_result = "unknown"

    trace_items: List[Dict[str, str]] = [
        {"label": "User", "value": user_text},
        {"label": "Agent decision", "value": decision},
        {"label": "DB result", "value": db_result},
        {"label": "System result", "value": system_result},
    ]
    if remaining_tasks is not None:
        trace_items.append({"label": "Remaining tasks", "value": str(remaining_tasks)})

    return {
        "items": trace_items,
        "raw_action": action,  # keep raw JSON too (dev gold)
    }
