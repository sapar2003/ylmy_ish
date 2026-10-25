from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import ExamKind, TimetableStatus
from app.schemas.structure import ReadBase
from app.schemas.timetable import Ref


def _check_weekdays(v: list[int] | None) -> list[int] | None:
    if v is None:
        return v
    if not v or any(d < 1 or d > 7 for d in v):
        raise ValueError("weekdays 1..7 aralykda bolmaly we boş bolmaly däl")
    return sorted(set(v))


# --- Synag möwsümi ---
class ExamSessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: ExamKind
    starts_on: date
    ends_on: date
    weekdays: list[int] = Field(default=[1, 2, 3, 4, 5, 6], description="1 = duşenbe ... 7 = ýekşenbe")
    max_per_day: int = Field(default=1, ge=1, le=4, description="Bir toparyň günde iň köp synagy")
    rest_days: int = Field(default=0, ge=0, le=7, description="Toparyň iki synagynyň arasynda iň az boş gün")

    _weekdays = field_validator("weekdays")(_check_weekdays)

    @model_validator(mode="after")
    def _order(self):
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on starts_on-dan öň bolmaly däl")
        return self


class ExamSessionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: ExamKind | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    weekdays: list[int] | None = None
    max_per_day: int | None = Field(default=None, ge=1, le=4)
    rest_days: int | None = Field(default=None, ge=0, le=7)

    _weekdays = field_validator("weekdays")(_check_weekdays)


class ExamSessionRead(ReadBase, ExamSessionCreate):
    pass


# --- Synag wagty ---
class ExamPeriodCreate(BaseModel):
    session_id: int
    number: int = Field(ge=1, le=12)
    starts_at: time
    ends_at: time

    @model_validator(mode="after")
    def _order(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at starts_at-dan soň bolmaly")
        return self


class ExamPeriodUpdate(BaseModel):
    number: int | None = Field(default=None, ge=1, le=12)
    starts_at: time | None = None
    ends_at: time | None = None


class ExamPeriodRead(ReadBase, ExamPeriodCreate):
    pass


# --- Synag ---
class ExamCreate(BaseModel):
    session_id: int
    subject_id: int
    group_id: int | None = None
    stream_id: int | None = None
    examiner_id: int = Field(description="Uly mugallym (synagy alýan)")
    assistant_id: int | None = Field(default=None, description="Kiçi mugallym (kömekçi)")
    room_type_id: int | None = None


class ExamUpdate(BaseModel):
    session_id: int | None = None
    subject_id: int | None = None
    group_id: int | None = None
    stream_id: int | None = None
    examiner_id: int | None = None
    assistant_id: int | None = None
    room_type_id: int | None = None


class ExamRead(ReadBase, ExamCreate):
    pass


# --- Synag raspisaniýesi ---
class ExamScheduleCreate(BaseModel):
    session_id: int
    name: str = Field(min_length=1, max_length=200)
    time_limit_seconds: int = Field(default=60, ge=5, le=3600)


class ExamScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    name: str
    status: TimetableStatus
    time_limit_seconds: int
    solver_status: str | None
    issues: list[str]
    objective: float | None
    seconds: float | None
    created_at: datetime
    entry_count: int = 0


class ExamEntryRead(BaseModel):
    id: int
    exam_id: int
    day: date
    weekday: int
    period: int
    starts_at: time
    ends_at: time
    subject: Ref
    examiner: Ref
    assistant: Ref | None
    room: Ref | None
    groups: list[Ref]
    stream: Ref | None


class ExamPrecheckRead(BaseModel):
    exams: int
    days: int
    slots: int
    issues: list[str]
