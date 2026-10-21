"""Düzülen raspisaniýeler. Her generasiýa täze `Timetable` döredýär, köne wersiýalar saklanýar."""
import enum

from sqlalchemy import JSON, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class TimetableStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Timetable(IdMixin, TimestampMixin, Base):
    __tablename__ = "timetables"

    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[TimetableStatus] = mapped_column(
        Enum(TimetableStatus, name="timetable_status"), default=TimetableStatus.pending
    )
    time_limit_seconds: Mapped[int] = mapped_column(default=60)
    solver_status: Mapped[str | None] = mapped_column(String(50))
    issues: Mapped[list[str]] = mapped_column(JSON, default=list)
    objective: Mapped[float | None] = mapped_column(Float)
    seconds: Mapped[float | None] = mapped_column(Float)

    entries: Mapped[list["TimetableEntry"]] = relationship(
        back_populates="timetable", cascade="all, delete-orphan", passive_deletes=True
    )


class TimetableEntry(IdMixin, Base):
    """Bir sapak bir wagtda bir otagda."""

    __tablename__ = "timetable_entries"

    timetable_id: Mapped[int] = mapped_column(ForeignKey("timetables.id", ondelete="CASCADE"), index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("teaching_assignments.id", ondelete="CASCADE"))
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id", ondelete="CASCADE"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))

    timetable: Mapped[Timetable] = relationship(back_populates="entries")
