from datetime import time

from pydantic import BaseModel, Field, model_validator

from app.models import AvailabilityStatus
from app.schemas.structure import ReadBase


def _check_time_order(starts_at: time | None, ends_at: time | None) -> None:
    if starts_at and ends_at and ends_at <= starts_at:
        raise ValueError("ends_at starts_at-dan soň bolmaly")


# --- Mugallym ---
class TeacherCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    position: str | None = Field(default=None, max_length=100)
    department_id: int
    max_lessons_per_week: int | None = Field(default=None, ge=1)
    max_lessons_per_day: int | None = Field(default=None, ge=1)


class TeacherUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    position: str | None = Field(default=None, max_length=100)
    department_id: int | None = None
    max_lessons_per_week: int | None = Field(default=None, ge=1)
    max_lessons_per_day: int | None = Field(default=None, ge=1)


class TeacherRead(ReadBase, TeacherCreate):
    pass


class AvailabilityItem(BaseModel):
    time_slot_id: int
    status: AvailabilityStatus


# --- Wagt sloty ---
class TimeSlotCreate(BaseModel):
    shift_id: int
    weekday: int = Field(ge=1, le=7, description="1 = duşenbe ... 7 = ýekşenbe")
    number: int = Field(ge=1, le=12)
    starts_at: time
    ends_at: time

    @model_validator(mode="after")
    def _order(self):
        _check_time_order(self.starts_at, self.ends_at)
        return self


class TimeSlotUpdate(BaseModel):
    weekday: int | None = Field(default=None, ge=1, le=7)
    number: int | None = Field(default=None, ge=1, le=12)
    starts_at: time | None = None
    ends_at: time | None = None


class TimeSlotRead(ReadBase, TimeSlotCreate):
    pass


class LessonPeriod(BaseModel):
    number: int = Field(ge=1, le=12)
    starts_at: time
    ends_at: time

    @model_validator(mode="after")
    def _order(self):
        _check_time_order(self.starts_at, self.ends_at)
        return self


class TimeSlotGenerate(BaseModel):
    """Bir smena üçin ähli günleriň slotlaryny bir gezekde döretmek."""

    shift_id: int
    weekdays: list[int] = Field(default=[1, 2, 3, 4, 5, 6], min_length=1)
    periods: list[LessonPeriod] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self):
        if any(d < 1 or d > 7 for d in self.weekdays):
            raise ValueError("weekdays 1..7 aralykda bolmaly")
        if len({p.number for p in self.periods}) != len(self.periods):
            raise ValueError("periods-da sapak belgisi gaýtalanýar")
        return self


# --- Bina, otag ---
class BuildingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str | None = Field(default=None, max_length=300)


class BuildingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, max_length=300)


class BuildingRead(ReadBase, BuildingCreate):
    pass


class RoomTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class RoomTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class RoomTypeRead(ReadBase, RoomTypeCreate):
    pass


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    capacity: int = Field(gt=0)
    building_id: int
    room_type_id: int


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    capacity: int | None = Field(default=None, gt=0)
    building_id: int | None = None
    room_type_id: int | None = None


class RoomRead(ReadBase, RoomCreate):
    pass
