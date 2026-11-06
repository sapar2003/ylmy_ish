"""Talyplar we gündelik bahalar (žurnal).

Baha bir sapak gününe degişli: mugallymyň okadýan sapagy (TeachingAssignment) + sene + wagt sloty.
Bahalar: 2, 3, 4, 5 we "gm" (gatnaşmady). Her üýtgeşme MarkLog-a ýazylýar.
"""
import enum
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class MarkValue(str, enum.Enum):
    two = "2"
    three = "3"
    four = "4"
    five = "5"
    absent = "gm"  # gatnaşmady


class Student(IdMixin, TimestampMixin, Base):
    __tablename__ = "students"

    full_name: Mapped[str] = mapped_column(String(200))
    number: Mapped[str | None] = mapped_column(String(30))  # talyp belgisi (bar bolsa)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)  # app-a giriş üçin: +9936XXXXXXX
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="RESTRICT"), index=True)
    subgroup_id: Mapped[int | None] = mapped_column(ForeignKey("subgroups.id", ondelete="SET NULL"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Mark(IdMixin, TimestampMixin, Base):
    __tablename__ = "marks"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", "day", "time_slot_id"),)

    assignment_id: Mapped[int] = mapped_column(ForeignKey("teaching_assignments.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id", ondelete="CASCADE"))
    value: Mapped[MarkValue] = mapped_column(Enum(MarkValue, name="mark_value", values_callable=lambda e: [x.value for x in e]))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class MarkLog(IdMixin, TimestampMixin, Base):
    """Bahanyň her üýtgeşmesi: kim, haçan, köne we täze baha (None — aýryldy)."""

    __tablename__ = "mark_logs"

    assignment_id: Mapped[int] = mapped_column(ForeignKey("teaching_assignments.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id", ondelete="CASCADE"))
    old_value: Mapped[str | None] = mapped_column(String(5))
    new_value: Mapped[str | None] = mapped_column(String(5))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
