"""Sapagyň temasy we prezentasiýasy: mugallym öz sapagyna (sapak güni boýunça) tema we faýl goýýar,
şol sapagy okaýan talyplar görýär. Faýl diskde `settings.upload_dir` bukjasynda saklanýar."""
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class LessonTopic(IdMixin, TimestampMixin, Base):
    __tablename__ = "lesson_topics"
    __table_args__ = (UniqueConstraint("assignment_id", "day", "time_slot_id"),)

    assignment_id: Mapped[int] = mapped_column(ForeignKey("teaching_assignments.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id", ondelete="CASCADE"))
    topic: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str | None] = mapped_column(Text)  # goşmaça düşündiriş (öý işi we ş.m.)
    file_name: Mapped[str | None] = mapped_column(String(200))  # talyba görünýän ady
    file_key: Mapped[str | None] = mapped_column(String(100))  # diskdäki ady
    file_size: Mapped[int | None] = mapped_column(Integer)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
