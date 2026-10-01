import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app import crud, reminders
from app.database import get_db
from app.models import Todo
from app.reminders import redis_client
from app.schemas import TodoCreate, TodoRead, TodoUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/todos", tags=["todos"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_or_404(db: Session, todo_id: int) -> Todo:
    todo = crud.get_todo(db, todo_id)
    if todo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Todo {todo_id} not found")
    return todo


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(data: TodoCreate, db: DbSession, request: Request, response: Response) -> Todo:
    todo = crud.create_todo(db, data)
    reminders.sync(redis_client, todo)
    response.headers["Location"] = str(request.url_for("get_todo", todo_id=todo.id))
    logger.info("Created todo %s", todo.id)
    return todo


@router.get("", response_model=list[TodoRead])
def list_todos(
    db: DbSession,
    completed: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Todo]:
    return crud.list_todos(db, completed=completed, limit=limit, offset=offset)


@router.get("/{todo_id}", response_model=TodoRead)
def get_todo(todo_id: int, db: DbSession) -> Todo:
    return _get_or_404(db, todo_id)


@router.patch("/{todo_id}", response_model=TodoRead)
def update_todo(todo_id: int, data: TodoUpdate, db: DbSession) -> Todo:
    todo = crud.update_todo(db, _get_or_404(db, todo_id), data)
    reminders.sync(redis_client, todo)
    logger.info("Updated todo %s", todo_id)
    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, db: DbSession) -> None:
    crud.delete_todo(db, _get_or_404(db, todo_id))
    reminders.cancel(redis_client, todo_id)
    logger.info("Deleted todo %s", todo_id)
