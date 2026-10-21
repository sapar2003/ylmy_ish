"""Uniwersitetiň gurluşy: fakultet -> kafedra -> hünär -> topar -> kiçi topar.

Ähli ýazgylar ulanyjy tarapyndan goşulýar we aýrylýar; kodda hiç bir fakultet berkidilmeýär.
"""
import enum
from datetime import time

from sqlalchemy import Enum, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class StudyLevel(str, enum.Enum):
    bachelor = "bachelor"
    master = "master"


class Faculty(IdMixin, TimestampMixin, Base):
    __tablename__ = "faculties"

    name: Mapped[str] = mapped_column(String(200), unique=True)
    short_name: Mapped[str | None] = mapped_column(String(50))
    code: Mapped[str | None] = mapped_column(String(20), unique=True)

    departments: Mapped[list["Department"]] = relationship(back_populates="faculty")


class Department(IdMixin, TimestampMixin, Base):
    """Kafedra. Mugallymlar kafedra degişli, fakultete däl."""

    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("faculty_id", "name"),)

    name: Mapped[str] = mapped_column(String(200))
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id", ondelete="RESTRICT"), index=True)

    faculty: Mapped[Faculty] = relationship(back_populates="departments")
    specialties: Mapped[list["Specialty"]] = relationship(back_populates="department")


class Specialty(IdMixin, TimestampMixin, Base):
    """Hünär (bakalawr ýa-da magistr)."""

    __tablename__ = "specialties"
    __table_args__ = (UniqueConstraint("department_id", "name", "level"),)

    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str | None] = mapped_column(String(30))
    level: Mapped[StudyLevel] = mapped_column(Enum(StudyLevel, name="study_level"))
    duration_years: Mapped[int] = mapped_column(default=4)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), index=True)

    department: Mapped[Department] = relationship(back_populates="specialties")
    groups: Mapped[list["Group"]] = relationship(back_populates="specialty")


class Shift(IdMixin, TimestampMixin, Base):
    """Smena: irden, öýlän ýa-da ulanyjynyň goşan başga smenasy."""

    __tablename__ = "shifts"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    starts_at: Mapped[time] = mapped_column(Time)
    ends_at: Mapped[time] = mapped_column(Time)


class Group(IdMixin, TimestampMixin, Base):
    """Topar. Smena toparyň üstünde: topar diňe öz smenasynda okaýar."""

    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    course: Mapped[int]
    student_count: Mapped[int] = mapped_column(default=0)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id", ondelete="RESTRICT"), index=True)
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id", ondelete="RESTRICT"))

    specialty: Mapped[Specialty] = relationship(back_populates="groups")
    subgroups: Mapped[list["Subgroup"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )


class Subgroup(IdMixin, TimestampMixin, Base):
    """Kiçi topar: bir sapak 2 (ýa-da has köp) bölege bölünende ulanylýar."""

    __tablename__ = "subgroups"
    __table_args__ = (UniqueConstraint("group_id", "name"),)

    name: Mapped[str] = mapped_column(String(50))
    student_count: Mapped[int] = mapped_column(default=0)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)

    group: Mapped[Group] = relationship(back_populates="subgroups")
