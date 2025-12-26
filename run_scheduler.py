from assistant.db import init_db
from assistant.scheduler import run_scheduler

if __name__ == "__main__":
    init_db()
    run_scheduler(tick_seconds=1.0)
