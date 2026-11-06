"""Programma ulanyjylary: admin (okuw bölümi) raspisaniýe düzýär, dekan diňe öz fakultetiniň maglumatlaryny
girizýär, mugallym diňe öz raspisaniýesini görýär. Täze rol üçin `Role`-a baha goşmak ýeterlik."""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Role(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    dean = "dean"  # okuw işleri boýunça dekanyň orunbasary: diňe öz fakulteti
    student = "student"  # talyp: telefon nomeri bilen app-a girýär


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"))
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), unique=True, index=True
    )
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculties.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), unique=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginCode(IdMixin, TimestampMixin, Base):
    """Telefon nomerine iberilen bir gezeklik giriş kody (bir nomere bir ýazgy; kod heş görnüşinde)."""

    __tablename__ = "login_codes"

    phone: Mapped[str] = mapped_column(String(20), unique=True)
    code_hash: Mapped[str] = mapped_column(String(200))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(default=0)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime)
    window_start: Mapped[datetime] = mapped_column(DateTime)  # sagatlyk çäk üçin
    sent_in_window: Mapped[int] = mapped_column(default=0)
