from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.models import LessonType, TimetableStatus


class TimetableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    time_limit_seconds: int = Field(default=60, ge=5, le=3600)


class TimetableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: TimetableStatus
    time_limit_seconds: int
    solver_status: str | None
    issues: list[str]
    objective: float | None
    seconds: float | None
    created_at: datetime
    entry_count: int = 0


class Ref(BaseModel):
    id: int
    name: str


class EntryRead(BaseModel):
    id: int
    time_slot_id: int
    weekday: int
    number: int
    starts_at: time
    ends_at: time
    subject: Ref
    lesson_type: LessonType
    teacher: Ref
    room: Ref | None
    groups: list[Ref]
    subgroup: Ref | None
    stream: Ref | None


class PrecheckRead(BaseModel):
    lessons: int
    lessons_per_week: int
    issues: list[str]
