from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.models import Todo
from app.reminders import QUEUE_KEY
from app.worker import process_due, resync


def add_todo(**fields) -> int:
    with SessionLocal() as db:
        todo = Todo(title="Task", **fields)
        db.add(todo)
        db.commit()
        return todo.id


def queue(redis, todo_id: int, when: datetime) -> None:
    redis.zadd(QUEUE_KEY, {str(todo_id): when.timestamp()})


def test_due_reminder_is_sent_once(redis):
    remind_at = datetime.now(UTC) - timedelta(seconds=1)
    todo_id = add_todo(remind_at=remind_at)
    queue(redis, todo_id, remind_at)

    assert process_due(redis, datetime.now(UTC)) == 1
    assert process_due(redis, datetime.now(UTC)) == 0
    with SessionLocal() as db:
        assert db.get(Todo, todo_id).reminder_sent_at is not None


def test_future_reminder_is_not_sent(redis):
    remind_at = datetime.now(UTC) + timedelta(hours=1)
    todo_id = add_todo(remind_at=remind_at)
    queue(redis, todo_id, remind_at)

    assert process_due(redis, datetime.now(UTC)) == 0
    assert redis.zscore(QUEUE_KEY, str(todo_id)) is not None


def test_stale_entries_are_skipped(redis):
    past = datetime.now(UTC) - timedelta(seconds=1)
    completed_id = add_todo(remind_at=past, completed=True)
    queue(redis, completed_id, past)
    queue(redis, 999, past)

    assert process_due(redis, datetime.now(UTC)) == 0
    assert redis.zcard(QUEUE_KEY) == 0


def test_resync_restores_pending_reminders(redis):
    pending_id = add_todo(remind_at=datetime.now(UTC) + timedelta(hours=1))
    add_todo(remind_at=datetime.now(UTC), reminder_sent_at=datetime.now(UTC))
    add_todo()

    assert resync(redis) == 1
    assert redis.zrange(QUEUE_KEY, 0, -1) == [str(pending_id)]
