from datetime import UTC, datetime, timedelta

from app.reminders import QUEUE_KEY

API = "/api/v1/todos"


def future(minutes: int = 10) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


def test_create_todo(client):
    response = client.post(API, json={"title": "Buy milk", "description": "2 liters"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Buy milk"
    assert body["completed"] is False
    assert response.headers["location"].endswith(f"{API}/{body['id']}")


def test_create_todo_validation(client):
    assert client.post(API, json={"title": ""}).status_code == 422
    assert client.post(API, json={"title": "x", "unknown": 1}).status_code == 422
    no_timezone = datetime.now().replace(tzinfo=None) + timedelta(hours=1)
    assert (
        client.post(API, json={"title": "x", "remind_at": no_timezone.isoformat()}).status_code
        == 422
    )
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    assert client.post(API, json={"title": "x", "remind_at": past}).status_code == 422


def test_get_todo(client):
    todo_id = client.post(API, json={"title": "Read"}).json()["id"]

    assert client.get(f"{API}/{todo_id}").json()["title"] == "Read"
    assert client.get(f"{API}/999").status_code == 404


def test_list_todos_filter_and_pagination(client):
    ids = [client.post(API, json={"title": title}).json()["id"] for title in ("a", "b", "c")]
    client.patch(f"{API}/{ids[0]}", json={"completed": True})

    assert len(client.get(API).json()) == 3
    assert [t["title"] for t in client.get(API, params={"completed": True}).json()] == ["a"]
    assert [t["title"] for t in client.get(API, params={"limit": 1, "offset": 1}).json()] == ["b"]
    assert client.get(API, params={"limit": 0}).status_code == 422


def test_update_todo(client):
    todo_id = client.post(API, json={"title": "Old"}).json()["id"]

    response = client.patch(f"{API}/{todo_id}", json={"title": "New", "completed": True})

    assert response.status_code == 200
    assert response.json()["title"] == "New"
    assert response.json()["completed"] is True
    assert client.patch(f"{API}/{todo_id}", json={"title": None}).status_code == 422
    assert client.patch(f"{API}/999", json={"title": "x"}).status_code == 404


def test_delete_todo(client):
    todo_id = client.post(API, json={"title": "Temp"}).json()["id"]

    assert client.delete(f"{API}/{todo_id}").status_code == 204
    assert client.get(f"{API}/{todo_id}").status_code == 404
    assert client.delete(f"{API}/{todo_id}").status_code == 404


def test_reminder_is_queued_and_removed(client, redis):
    todo_id = client.post(API, json={"title": "Call", "remind_at": future()}).json()["id"]
    assert redis.zscore(QUEUE_KEY, str(todo_id)) is not None

    client.patch(f"{API}/{todo_id}", json={"completed": True})
    assert redis.zscore(QUEUE_KEY, str(todo_id)) is None

    client.patch(f"{API}/{todo_id}", json={"completed": False, "remind_at": future(20)})
    assert redis.zscore(QUEUE_KEY, str(todo_id)) is not None

    client.delete(f"{API}/{todo_id}")
    assert redis.zscore(QUEUE_KEY, str(todo_id)) is None
