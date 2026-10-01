from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


def _check_future(value: datetime | None) -> datetime | None:
    if value is not None and value <= datetime.now(UTC):
        raise ValueError("must be in the future")
    return value


class TodoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_at: AwareDatetime | None = None
    remind_at: AwareDatetime | None = None

    @field_validator("remind_at")
    @classmethod
    def remind_at_in_future(cls, value: datetime | None) -> datetime | None:
        return _check_future(value)


class TodoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    completed: bool | None = None
    due_at: AwareDatetime | None = None
    remind_at: AwareDatetime | None = None

    @field_validator("title", "completed")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("may not be null")
        return value

    @field_validator("remind_at")
    @classmethod
    def remind_at_in_future(cls, value: datetime | None) -> datetime | None:
        return _check_future(value)


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    completed: bool
    due_at: datetime | None
    remind_at: datetime | None
    reminder_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
