from dotenv import load_dotenv

load_dotenv(".env.test", override=True)

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text

from app.config import settings
from app.database import engine
from app.main import app
from app.reminders import redis_client


@pytest.fixture(scope="session", autouse=True)
def database():
    url = make_url(settings.database_url)
    if not url.database or not url.database.endswith("_test"):
        pytest.exit(f"Refusing to run tests against database {url.database!r}", returncode=1)

    server = create_engine(url.set(database=""))
    with server.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{url.database}`"))
    command.upgrade(Config("alembic.ini"), "head")
    yield
    redis_client.flushdb()
    engine.dispose()
    with server.begin() as conn:
        conn.execute(text(f"DROP DATABASE `{url.database}`"))
    server.dispose()


@pytest.fixture(autouse=True)
def clean_state():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM todos"))
    redis_client.flushdb()


@pytest.fixture
def redis():
    return redis_client


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
