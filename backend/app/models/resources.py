"""Resurslar: mugallymlar, binalar, otaglar we wagt slotlary."""
import enum
from datetime import time

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class AvailabilityStatus(str, enum.Enum):
    available = "available"  # bolup bilýär
    preferred = "preferred"  # isleýär
    unavailable = "unavailable"  # bolmaz


class Teacher(IdMixin, TimestampMixin, Base):
    """Mugallym kafedra degişli. Islendik fakultetiň toparyna okadyp bilýär,
    şonuň üçin onuň ähli sapaklary bir umumy wagt setkasynda barlanýar."""

    __tablename__ = "teachers"

    name: Mapped[str] = mapped_column(String(200))
    position: Mapped[str | None] = mapped_column(String(100))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), index=True)
    max_lessons_per_week: Mapped[int | None]
    max_lessons_per_day: Mapped[int | None]

    availability: Mapped[list["TeacherAvailability"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan", passive_deletes=True
    )


class TimeSlot(IdMixin, TimestampMixin, Base):
    """Bir smenadaky bir sapak wagty, meselem: duşenbe, irden, 2-nji jübüt, 10:00-11:20."""

    __tablename__ = "time_slots"
    __table_args__ = (
        UniqueConstraint("shift_id", "weekday", "number"),
        CheckConstraint("weekday BETWEEN 1 AND 7", name="weekday_range"),
        CheckConstraint("ends_at > starts_at", name="slot_time_order"),
    )

    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id", ondelete="RESTRICT"), index=True)
    weekday: Mapped[int]  # 1 = duşenbe ... 7 = ýekşenbe
    number: Mapped[int]  # smenadaky n-nji sapak
    starts_at: Mapped[time] = mapped_column(Time)
    ends_at: Mapped[time] = mapped_column(Time)


class TeacherAvailability(IdMixin, TimestampMixin, Base):
    """Ýazgy ýok bolsa, mugallym şol slotda boş hasaplanýar."""

    __tablename__ = "teacher_availability"
    __table_args__ = (UniqueConstraint("teacher_id", "time_slot_id"),)

    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id", ondelete="CASCADE"))
    status: Mapped[AvailabilityStatus] = mapped_column(Enum(AvailabilityStatus, name="availability_status"))

    teacher: Mapped[Teacher] = relationship(back_populates="availability")


class Building(IdMixin, TimestampMixin, Base):
    __tablename__ = "buildings"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    address: Mapped[str | None] = mapped_column(String(300))


class RoomType(IdMixin, TimestampMixin, Base):
    """Otag görnüşi ulanyjy tarapyndan goşulýar: leksiýa zaly, laboratoriýa, kompýuter otagy..."""

    __tablename__ = "room_types"

    name: Mapped[str] = mapped_column(String(100), unique=True)


class Room(IdMixin, TimestampMixin, Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("building_id", "name"),
        CheckConstraint("capacity > 0", name="room_capacity_positive"),
    )

    name: Mapped[str] = mapped_column(String(50))
    capacity: Mapped[int]
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="RESTRICT"), index=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id", ondelete="RESTRICT"), index=True)
