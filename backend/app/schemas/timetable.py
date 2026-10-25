from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import LessonType, TimetableStatus


class TimetableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    time_limit_seconds: int = Field(default=60, ge=5, le=3600)
    weeks: int = Field(default=1, ge=1, le=2, description="2: 1-nji we 2-nji hepde (sanawjy/maýdalawjy)")
    starts_on: date | None = Field(default=None, description="Ýarymýylyň başy: 1-nji hepde şu senäniň hepdesi")
    ends_on: date | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on starts_on-dan öň bolmaly däl")
        return self


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
    weeks: int
    starts_on: date | None
    ends_on: date | None


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
    week: int | None = None  # None: her hepde; 1 ýa-da 2: diňe şol hepde


class PrecheckRead(BaseModel):
    lessons: int
    lessons_per_week: int
    issues: list[str]
