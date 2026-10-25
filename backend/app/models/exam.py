"""Synag raspisaniýesi: synag möwsümi (ara synag, ýarymýyllyk synag, ...), onuň wagtlary we synaglar.

Hepdelik raspisaniýeden tapawudy: synag belli bir senede geçýär we her synag diňe bir gezek bolýar.
Täze synag görnüşi goşmak üçin diňe `ExamKind`-e baha goşmak ýeterlik.
"""
import enum
from datetime import date, time

from sqlalchemy import JSON, CheckConstraint, Date, Enum, Float, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.models.timetable import TimetableStatus


class ExamKind(str, enum.Enum):
    midterm = "midterm"  # ara synag
    final = "final"  # ýarymýyllyk synag
    retake = "retake"  # gaýtadan tabşyrmak
    state = "state"  # döwlet synagy
    other = "other"


class ExamSession(IdMixin, TimestampMixin, Base):
    """Synag möwsümi: synaglaryň geçýän senesi we düzgünleri."""

    __tablename__ = "exam_sessions"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="exam_session_dates"),
        CheckConstraint("max_per_day >= 1", name="exam_max_per_day"),
        CheckConstraint("rest_days >= 0", name="exam_rest_days"),
    )

    name: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[ExamKind] = mapped_column(Enum(ExamKind, name="exam_kind"))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    weekdays: Mapped[list[int]] = mapped_column(JSON, default=lambda: [1, 2, 3, 4, 5, 6])  # synag bolýan günler
    max_per_day: Mapped[int] = mapped_column(default=1)  # bir toparyň günde iň köp synagy
    rest_days: Mapped[int] = mapped_column(default=0)  # toparyň iki synagynyň arasynda iň az boş gün

    periods: Mapped[list["ExamPeriod"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True, order_by="ExamPeriod.number"
    )


class ExamPeriod(IdMixin, TimestampMixin, Base):
    """Synag gününiň bir wagty, meselem: 1-nji, 09:00-10:20."""

    __tablename__ = "exam_periods"
    __table_args__ = (
        UniqueConstraint("session_id", "number"),
        CheckConstraint("ends_at > starts_at", name="exam_period_time_order"),
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id", ondelete="CASCADE"), index=True)
    number: Mapped[int]
    starts_at: Mapped[time] = mapped_column(Time)
    ends_at: Mapped[time] = mapped_column(Time)

    session: Mapped[ExamSession] = relationship(back_populates="periods")


class Exam(IdMixin, TimestampMixin, Base):
    """Bir toparyň (ýa-da potoguň) bir dersden synagy.

    Uly mugallym synagy alýar, kiçi mugallym kömekçi; ikisi hem şol wagt başga ýerde bolup bilmeýär.
    """

    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint("(group_id IS NULL) <> (stream_id IS NULL)", name="exam_group_xor_stream"),
        CheckConstraint("assistant_id IS NULL OR assistant_id <> examiner_id", name="exam_two_teachers"),
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), index=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="RESTRICT"), index=True)
    stream_id: Mapped[int | None] = mapped_column(ForeignKey("streams.id", ondelete="RESTRICT"), index=True)
    examiner_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    assistant_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    room_type_id: Mapped[int | None] = mapped_column(ForeignKey("room_types.id", ondelete="RESTRICT"))


class ExamSchedule(IdMixin, TimestampMixin, Base):
    """Bir synag möwsümi üçin düzülen raspisaniýe. Her düzülişi täze wersiýa, köneleri saklanýar."""

    __tablename__ = "exam_schedules"

    session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[TimetableStatus] = mapped_column(
        Enum(TimetableStatus, name="exam_schedule_status"), default=TimetableStatus.pending
    )
    time_limit_seconds: Mapped[int] = mapped_column(default=60)
    solver_status: Mapped[str | None] = mapped_column(String(50))
    issues: Mapped[list[str]] = mapped_column(JSON, default=list)
    objective: Mapped[float | None] = mapped_column(Float)
    seconds: Mapped[float | None] = mapped_column(Float)

    entries: Mapped[list["ExamEntry"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan", passive_deletes=True
    )


class ExamEntry(IdMixin, Base):
    """Bir synag: haýsy gün, haýsy wagtda, haýsy otagda."""

    __tablename__ = "exam_entries"

    schedule_id: Mapped[int] = mapped_column(ForeignKey("exam_schedules.id", ondelete="CASCADE"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    period_id: Mapped[int] = mapped_column(ForeignKey("exam_periods.id", ondelete="CASCADE"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))

    schedule: Mapped[ExamSchedule] = relationship(back_populates="entries")
