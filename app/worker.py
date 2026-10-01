import logging
import signal
import threading
import time
from datetime import UTC, datetime

from redis import Redis

from app import crud, reminders
from app.config import settings
from app.database import SessionLocal
from app.log import setup_logging
from app.models import Todo

logger = logging.getLogger("app.worker")


def process_due(redis: Redis, now: datetime) -> int:
    sent = 0
    for todo_id in reminders.pop_due(redis, now):
        with SessionLocal() as db:
            todo = db.get(Todo, todo_id)
            if (
                todo is None
                or todo.completed
                or todo.reminder_sent_at is not None
                or todo.remind_at is None
                or todo.remind_at > now
            ):
                logger.info("Skipping stale reminder for todo %s", todo_id)
                continue
            logger.info(
                "REMINDER todo_id=%s title=%r remind_at=%s",
                todo.id,
                todo.title,
                todo.remind_at.isoformat(),
            )
            todo.reminder_sent_at = now
            db.commit()
            sent += 1
    return sent


def resync(redis: Redis) -> int:
    with SessionLocal() as db:
        todos = crud.pending_reminders(db)
    if todos:
        redis.zadd(reminders.QUEUE_KEY, {str(t.id): t.remind_at.timestamp() for t in todos})
    return len(todos)


def run() -> None:
    setup_logging()
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    redis = reminders.redis_client
    next_resync = 0.0
    logger.info("Reminder worker started")

    while not stop.is_set():
        try:
            if time.monotonic() >= next_resync:
                count = resync(redis)
                logger.debug("Resynced %d pending reminders", count)
                next_resync = time.monotonic() + settings.reminder_resync_seconds
            process_due(redis, datetime.now(UTC))
        except Exception:
            logger.exception("Reminder worker iteration failed")
        stop.wait(settings.reminder_poll_seconds)

    logger.info("Reminder worker stopped")


if __name__ == "__main__":
    run()
