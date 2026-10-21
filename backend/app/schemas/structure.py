from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import StudyLevel


class ReadBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# --- Fakultet ---
class FacultyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    short_name: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=20)


class FacultyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    short_name: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=20)


class FacultyRead(ReadBase, FacultyCreate):
    pass


# --- Kafedra ---
class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    faculty_id: int


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    faculty_id: int | None = None


class DepartmentRead(ReadBase, DepartmentCreate):
    pass


# --- Hünär ---
class SpecialtyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=30)
    level: StudyLevel
    duration_years: int = Field(default=4, ge=1, le=8)
    department_id: int


class SpecialtyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=30)
    level: StudyLevel | None = None
    duration_years: int | None = Field(default=None, ge=1, le=8)
    department_id: int | None = None


class SpecialtyRead(ReadBase, SpecialtyCreate):
    pass


# --- Smena ---
class ShiftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    starts_at: time
    ends_at: time

    @model_validator(mode="after")
    def _check_order(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at starts_at-dan soň bolmaly")
        return self


class ShiftUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    starts_at: time | None = None
    ends_at: time | None = None


class ShiftRead(ReadBase):
    name: str
    starts_at: time
    ends_at: time


# --- Topar ---
class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    course: int = Field(ge=1, le=8)
    student_count: int = Field(default=0, ge=0)
    specialty_id: int
    shift_id: int | None = None


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    course: int | None = Field(default=None, ge=1, le=8)
    student_count: int | None = Field(default=None, ge=0)
    specialty_id: int | None = None
    shift_id: int | None = None


class GroupRead(ReadBase, GroupCreate):
    pass


# --- Kiçi topar ---
class SubgroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    student_count: int = Field(default=0, ge=0)
    group_id: int


class SubgroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    student_count: int | None = Field(default=None, ge=0)


class SubgroupRead(ReadBase, SubgroupCreate):
    pass
