# Todo API

This is a simple Todo app with a REST API. You can create, read, update and delete todos.
You can also set a reminder time for a todo. When the time comes, a background worker
sends the reminder.

## Tech stack

- **API**: FastAPI on Python 3.14, Pydantic for validation
- **Storage**: MariaDB 13.0 through SQLAlchemy
- **Schema changes**: Alembic migrations
- **Reminder queue**: Redis 8.10 with a background worker
- **Runtime**: Docker Compose
- **Tests**: pytest

## Quick start

You need Docker and Docker Compose on your computer.

First, copy the example settings file. Then build and start all containers:

```bash
cp .env.example .env
docker compose up --build
```

When everything is running, you can open:

- API: http://localhost:8000
- Swagger UI (API docs, you can try the endpoints here): http://localhost:8000/docs
- ReDoc (API docs): http://localhost:8000/redoc

The database tables are created automatically before the API starts.

## Services

| Service   | Purpose                                                   |
|-----------|-----------------------------------------------------------|
| `migrate` | Runs `alembic upgrade head` once, then exits              |
| `api`     | FastAPI app                                               |
| `worker`  | Sends due reminders (`python -m app.worker`)              |
| `db`      | MariaDB 13.0                                              |
| `redis`   | Redis 8.10, reminder queue (sorted set), not persisted    |

## API

| Method   | Path                  | Description                      | Success |
|----------|-----------------------|----------------------------------|---------|
| `POST`   | `/api/v1/todos`       | Create a todo                    | 201     |
| `GET`    | `/api/v1/todos`       | List todos                       | 200     |
| `GET`    | `/api/v1/todos/{id}`  | Get one todo                     | 200     |
| `PATCH`  | `/api/v1/todos/{id}`  | Partially update a todo          | 200     |
| `DELETE` | `/api/v1/todos/{id}`  | Delete a todo                    | 204     |

List filters: `completed`, `limit` (1-100, default 50), `offset`.

Errors: `404` unknown todo, `422` invalid input (e.g. empty title, unknown fields,
`remind_at` in the past or without timezone), `503` database unavailable.

### Examples

```bash
curl -X POST localhost:8000/api/v1/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Submit report", "due_at": "2030-01-10T17:00:00Z", "remind_at": "2030-01-10T09:00:00Z"}'

curl localhost:8000/api/v1/todos?completed=false

curl -X PATCH localhost:8000/api/v1/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

curl -X DELETE localhost:8000/api/v1/todos/1
```

To see a reminder fire, set `remind_at` to about a minute from now and watch
`docker compose logs -f worker`.

## How reminders work

- MariaDB is the source of truth: each todo has `remind_at` and `reminder_sent_at`.
- On create/update the API puts the todo id into a Redis sorted set, scored by the
  reminder timestamp. Changing the time just updates the score; completing or
  deleting the todo removes it.
- The worker polls the set, claims due ids with `ZREM` (only one worker can win),
  re-checks the todo in the database and skips it if it was deleted, completed,
  rescheduled or already sent. Then it logs the reminder and sets `reminder_sent_at`.
- On start and every minute the worker re-adds all pending reminders from the database.
  Redis is therefore not persisted: if it restarts empty or was down when a todo was
  saved, reminders still go out.

## Local development

Requires Python 3.14.

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements-dev.txt
```

## Running tests

```bash
docker compose up -d db redis
pytest
```

They cover the CRUD endpoints, validation errors, 404s, reminder scheduling in Redis and
the worker (due, stale and already-sent reminders, and resync from the database).

Useful variants:

```bash
pytest -v                          # list every test
pytest tests/test_worker.py        # one file
pytest -k reminder                 # tests matching a name
```

## Configuration

All variables are set in `.env`. See `.env.example`.

| Variable                  | Default                    | Purpose                                        |
|---------------------------|----------------------------|------------------------------------------------|
| `DB_NAME`                 | `todo`                     | Database created by the MariaDB container      |
| `DB_USER`                 | `todo`                     | Database user created by the MariaDB container |
| `DB_PASSWORD`             | `todo`                     | Password of that user                          |
| `DB_ROOT_PASSWORD`        | `root`                     | MariaDB root password                          |
| `DATABASE_URL`            | required, no default       | Connection string used by the app, worker and migrations. Must match the `DB_*` values |
| `REDIS_URL`               | `redis://localhost:6379/0` | Redis connection (set to the `redis` container in Docker) |
| `API_PORT`                | `8000`                     | Port of the API on your computer               |
| `LOG_LEVEL`               | `INFO`                     | Log level                                      |
| `REMINDER_POLL_SECONDS`   | `5`                        | How often the worker checks for due reminders  |
| `REMINDER_RESYNC_SECONDS` | `60`                       | How often the worker copies pending reminders from the database back to Redis |
