"""Programma ulanyjylary: admin (okuw bölümi) raspisaniýe düzýär, dekan diňe öz fakultetiniň maglumatlaryny
girizýär, mugallym diňe öz raspisaniýesini görýär. Täze rol üçin `Role`-a baha goşmak ýeterlik."""
import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Role(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    dean = "dean"  # okuw işleri boýunça dekanyň orunbasary: diňe öz fakulteti


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"))
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), unique=True, index=True
    )
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculties.id", ondelete="CASCADE"), index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
