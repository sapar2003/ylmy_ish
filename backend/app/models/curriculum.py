"""Okuw meýilnamasy: haýsy topar haýsy dersi hepdede näçe gezek, kim bilen okaýar.

Bu tablisalar raspisaniýe algoritminiň esasy girişidir.
"""
import enum

from sqlalchemy import Boolean, CheckConstraint, Column, Enum, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.models.structure import Group


class LessonType(str, enum.Enum):
    lecture = "lecture"  # leksiýa
    practice = "practice"  # amaly sapak
    lab = "lab"  # tejribehana
    seminar = "seminar"


class Subject(IdMixin, TimestampMixin, Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("department_id", "name"),)

    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str | None] = mapped_column(String(30))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), index=True)


stream_groups = Table(
    "stream_groups",
    Base.metadata,
    Column("stream_id", ForeignKey("streams.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("groups.id", ondelete="RESTRICT"), primary_key=True),
)


class Stream(IdMixin, TimestampMixin, Base):
    """Potok: birnäçe topar bir leksiýany bilelikde diňleýär."""

    __tablename__ = "streams"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    groups: Mapped[list[Group]] = relationship(secondary=stream_groups)

    @property
    def group_ids(self) -> list[int]:
        return [g.id for g in self.groups]


class CurriculumItem(IdMixin, TimestampMixin, Base):
    """Bir topar (ýa-da potok) üçin bir dersiň bir görnüşi, meselem:
    "PO-101, Matematika, amaly sapak, hepdede 2 gezek, 2 kiçi topara bölünýär"."""

    __tablename__ = "curriculum_items"
    __table_args__ = (
        CheckConstraint("(group_id IS NULL) <> (stream_id IS NULL)", name="group_xor_stream"),
        CheckConstraint(
            "lessons_per_week >= 0 AND biweekly >= 0 AND lessons_per_week + biweekly > 0", name="lessons_positive"
        ),
    )

    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), index=True)
    lesson_type: Mapped[LessonType] = mapped_column(Enum(LessonType, name="lesson_type"))
    lessons_per_week: Mapped[int]  # her hepde
    biweekly: Mapped[int] = mapped_column(default=0, server_default="0")  # iki hepdede bir (1-nji ýa 2-nji hepde)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="RESTRICT"), index=True)
    stream_id: Mapped[int | None] = mapped_column(ForeignKey("streams.id", ondelete="RESTRICT"), index=True)
    split: Mapped[bool] = mapped_column(Boolean, default=False)  # kiçi toparlara bölünýärmi
    room_type_id: Mapped[int | None] = mapped_column(ForeignKey("room_types.id", ondelete="RESTRICT"))

    assignments: Mapped[list["TeachingAssignment"]] = relationship(
        back_populates="curriculum_item", cascade="all, delete-orphan", passive_deletes=True
    )


class TeachingAssignment(IdMixin, TimestampMixin, Base):
    """Kim okadýar. Bölünýän sapakda her kiçi topar üçin aýratyn ýazgy (mugallym dürli bolup biler)."""

    __tablename__ = "teaching_assignments"
    __table_args__ = (UniqueConstraint("curriculum_item_id", "subgroup_id"),)

    curriculum_item_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_items.id", ondelete="CASCADE"), index=True
    )
    subgroup_id: Mapped[int | None] = mapped_column(ForeignKey("subgroups.id", ondelete="RESTRICT"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)

    curriculum_item: Mapped[CurriculumItem] = relationship(back_populates="assignments")
