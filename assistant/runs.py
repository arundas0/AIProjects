import json
from typing import Any, Dict, Optional
from assistant.db import get_conn
from datetime import datetime, timezone

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_run(user_text: str, action: Dict[str, Any], system_result: str) -> int:
    created_at = now_iso()
    action_json = json.dumps(action, ensure_ascii=False)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO runs (user_text, action_json, system_result, created_at) VALUES (?, ?, ?, ?)",
            (user_text, action_json, system_result, created_at),
        )
        conn.commit()
        return int(cur.lastrowid)

def get_run(run_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT run_id, user_text, action_json, system_result, created_at FROM runs WHERE run_id=?",
            (run_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "run_id": row[0],
            "user_text": row[1],
            "action_json": row[2],
            "system_result": row[3],
            "created_at": row[4],
        }
