import logging
from datetime import datetime

from redis import Redis, RedisError

from app.config import settings
from app.models import Todo

logger = logging.getLogger(__name__)

QUEUE_KEY = "todos:reminders"

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def sync(redis: Redis, todo: Todo) -> None:
    try:
        if todo.remind_at and not todo.completed and todo.reminder_sent_at is None:
            redis.zadd(QUEUE_KEY, {str(todo.id): todo.remind_at.timestamp()})
        else:
            redis.zrem(QUEUE_KEY, str(todo.id))
    except RedisError:
        logger.exception("Could not update reminder queue for todo %s", todo.id)


def cancel(redis: Redis, todo_id: int) -> None:
    try:
        redis.zrem(QUEUE_KEY, str(todo_id))
    except RedisError:
        logger.exception("Could not remove reminder for todo %s", todo_id)


def pop_due(redis: Redis, now: datetime) -> list[int]:
    due = redis.zrangebyscore(QUEUE_KEY, "-inf", now.timestamp())
    # zrem only succeeds for one caller, so two workers never claim the same todo
    return [int(todo_id) for todo_id in due if redis.zrem(QUEUE_KEY, todo_id)]
