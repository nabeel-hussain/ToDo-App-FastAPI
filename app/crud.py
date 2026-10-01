from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Todo
from app.schemas import TodoCreate, TodoUpdate


def get_todo(db: Session, todo_id: int) -> Todo | None:
    return db.get(Todo, todo_id)


def list_todos(db: Session, *, completed: bool | None, limit: int, offset: int) -> list[Todo]:
    stmt = select(Todo).order_by(Todo.id).limit(limit).offset(offset)
    if completed is not None:
        stmt = stmt.where(Todo.completed == completed)
    return list(db.scalars(stmt))


def create_todo(db: Session, data: TodoCreate) -> Todo:
    todo = Todo(**data.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def update_todo(db: Session, todo: Todo, data: TodoUpdate) -> Todo:
    changes = data.model_dump(exclude_unset=True)
    if "remind_at" in changes and changes["remind_at"] != todo.remind_at:
        todo.reminder_sent_at = None
    for field, value in changes.items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo: Todo) -> None:
    db.delete(todo)
    db.commit()


def pending_reminders(db: Session) -> list[Todo]:
    stmt = select(Todo).where(
        Todo.remind_at.is_not(None),
        Todo.reminder_sent_at.is_(None),
        Todo.completed.is_(False),
    )
    return list(db.scalars(stmt))
