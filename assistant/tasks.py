from datetime import datetime
from .db import get_conn

def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()

def create_task(intent: str, title: str, due: str, notes: str) -> int:
    created_at = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (intent, title, due, notes, status, created_at) VALUES (?, ?, ?, ?, 'open', ?)",
            (intent, title, due or "", notes or "", created_at),
        )
        conn.commit()
        return int(cur.lastrowid)

def list_tasks(status: str = "open"):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, intent, title, due, notes, status, created_at, done_at "
            "FROM tasks WHERE status = ? ORDER BY (due = ''), due, id",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]

def mark_done(task_id: int) -> bool:
    done_at = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tasks SET status='done', done_at=? WHERE id=? AND status='open'",
            (done_at, task_id),
        )
        conn.commit()
        return cur.rowcount > 0

def delete_task(task_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM tasks WHERE id=?",
            (task_id,),
        )
        conn.commit()
        return cur.rowcount > 0

def find_open_by_title_fragment(fragment: str):
    frag = f"%{fragment.lower()}%"
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, due FROM tasks "
            "WHERE status='open' AND lower(title) LIKE ? "
            "ORDER BY (due = ''), due, id LIMIT 5",
            (frag,),
        ).fetchall()
        return [dict(r) for r in rows]
from datetime import datetime

def parse_iso(dt: str) -> datetime | None:
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt)
    except ValueError:
        return None

def fetch_due_reminders(now_iso: str):
    # Fetch open reminders that have a due datetime <= now
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, due, notes FROM tasks "
            "WHERE status='open' AND intent='create_reminder' AND due != '' AND due <= ? "
            "ORDER BY due, id",
            (now_iso,),
        ).fetchall()
        return [dict(r) for r in rows]
