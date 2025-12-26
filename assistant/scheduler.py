import time
from datetime import datetime
from .tasks import fetch_due_reminders, mark_done

def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()

def run_scheduler(tick_seconds: float = 1.0) -> None:
    """
    Polls every tick_seconds for due reminders and fires them.
    Keeps running until process exits.
    """
    print(f"[scheduler] Running (tick={tick_seconds}s)")
    while True:
        try:
            due = fetch_due_reminders(now_iso())
            for r in due:
                # Fire reminder
                print("\n🔔 REMINDER 🔔")
                print(f"#{r['id']} {r['title']}")
                if r.get("due"):
                    print(f"Due: {r['due']}")
                if r.get("notes"):
                    print(f"Notes: {r['notes']}")
                print("--------------\n")

                # Mark as done so it doesn't fire again
                mark_done(r["id"])

                # Optional: terminal beep
                print("\a", end="")  # may beep in some terminals

            time.sleep(tick_seconds)
        except KeyboardInterrupt:
            print("\n[scheduler] Stopped.")
            return
        except Exception as e:
            print(f"[scheduler] Error: {type(e).__name__}: {e}")
            time.sleep(tick_seconds)
