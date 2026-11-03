"""Dekanyň çägi: her ýazgy haýsy fakultete degişli we dekan haýsy ýazgylary görýär.

Fakultetiň eýeçiligi: kafedra → fakultet; hünär, mugallym, ders → kafedra; topar → hünär;
kiçi topar, talyp → topar; potok, okuw meýilnamasy, synag → topar(lar).
Dekan sanawlarda diňe öz fakultetiniňkini görýär (otaglarda — umumy otaglar hem). Başga fakultetiň
mugallymyny öz sapagyna bellemek üçin diňe saýlaw sanawy bar: `GET /teachers/choices`.
"""
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import models as m
from app.api.crud import Scope
from app.models.curriculum import stream_groups


def faculty_groups(faculty_id: int):
    return (select(m.Group.id)
            .join(m.Specialty, m.Specialty.id == m.Group.specialty_id)
            .join(m.Department, m.Department.id == m.Specialty.department_id)
            .where(m.Department.faculty_id == faculty_id))


def faculty_departments(faculty_id: int):
    return select(m.Department.id).where(m.Department.faculty_id == faculty_id)


def faculty_streams(faculty_id: int):
    return select(stream_groups.c.stream_id).where(stream_groups.c.group_id.in_(faculty_groups(faculty_id)))


def department_faculty(db: Session, department_id: int | None) -> int | None:
    dep = db.get(m.Department, department_id) if department_id else None
    return dep.faculty_id if dep else None


def group_faculty(db: Session, group_id: int | None) -> int | None:
    group = db.get(m.Group, group_id) if group_id else None
    spec = db.get(m.Specialty, group.specialty_id) if group else None
    return department_faculty(db, spec.department_id) if spec else None


def stream_faculty(db: Session, stream: m.Stream | None) -> int | None:
    """Potogyň ähli toparlary bir fakultetden bolsa — şol fakultet, ýogsam umumy (diňe admin)."""
    faculties = {group_faculty(db, g.id) for g in stream.groups} if stream else set()
    return faculties.pop() if len(faculties) == 1 else None


def item_faculty(db: Session, obj: Any) -> int | None:
    """Toparyň ýa-da potogyň sapagy/synagy (okuw meýilnamasy, synag)."""
    if obj.group_id:
        return group_faculty(db, obj.group_id)
    return stream_faculty(db, db.get(m.Stream, obj.stream_id) if obj.stream_id else None)


def _of_groups(model):
    return lambda f: or_(model.group_id.in_(faculty_groups(f)), model.stream_id.in_(faculty_streams(f)))


FACULTY = Scope(visible=lambda f: m.Faculty.id == f)
DEPARTMENT = Scope(owner=lambda db, o: o.faculty_id, visible=lambda f: m.Department.faculty_id == f)
SPECIALTY = Scope(owner=lambda db, o: department_faculty(db, o.department_id),
                  visible=lambda f: m.Specialty.department_id.in_(faculty_departments(f)))
GROUP = Scope(owner=lambda db, o: department_faculty(db, getattr(db.get(m.Specialty, o.specialty_id), "department_id", None)),
              visible=lambda f: m.Group.id.in_(faculty_groups(f)))
SUBGROUP = Scope(owner=lambda db, o: group_faculty(db, o.group_id), visible=lambda f: m.Subgroup.group_id.in_(faculty_groups(f)))
STUDENT = Scope(owner=lambda db, o: group_faculty(db, o.group_id), visible=lambda f: m.Student.group_id.in_(faculty_groups(f)))
TEACHER = Scope(owner=lambda db, o: department_faculty(db, o.department_id),
                visible=lambda f: m.Teacher.department_id.in_(faculty_departments(f)))
# Ders: öz kafedralarynyňky we öz meýilnamasynda/synaglarynda bolan (meselem, umumy kafedranyň dersi).
SUBJECT = Scope(owner=lambda db, o: department_faculty(db, o.department_id),
                visible=lambda f: or_(m.Subject.department_id.in_(faculty_departments(f)),
                                      m.Subject.id.in_(select(m.CurriculumItem.subject_id).where(_of_groups(m.CurriculumItem)(f))),
                                      m.Subject.id.in_(select(m.Exam.subject_id).where(_of_groups(m.Exam)(f)))))
ROOM = Scope(owner=lambda db, o: o.faculty_id, visible=lambda f: or_(m.Room.faculty_id == f, m.Room.faculty_id.is_(None)))
STREAM = Scope(owner=stream_faculty, visible=lambda f: m.Stream.id.in_(faculty_streams(f)))
CURRICULUM = Scope(owner=item_faculty, visible=_of_groups(m.CurriculumItem))
ASSIGNMENT = Scope(
    owner=lambda db, o: item_faculty(db, db.get(m.CurriculumItem, o.curriculum_item_id)) if o.curriculum_item_id else None,
    visible=lambda f: m.TeachingAssignment.curriculum_item_id.in_(
        select(m.CurriculumItem.id).where(_of_groups(m.CurriculumItem)(f))),
)
EXAM = Scope(owner=item_faculty, visible=_of_groups(m.Exam))
