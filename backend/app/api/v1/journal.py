"""Talyplar (admin) we gündelik bahalar: mugallym öz sapagyna, admin islendik sapaga baha goýýar."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app import models as m
from app.api import scope as sc
from app.api.auth import CurrentUser, FacultyScope, TeacherUser, require_admin, require_staff
from app.api.crud import DbSession, build_crud_router, check_owner, get_or_404
from app.schemas.structure import ReadBase
from app.services import journal as j
from app.services.accounts import clean_phone
from app.services.students import create_demo_students

router = APIRouter()


# --- talyplar (admin) ---
class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    number: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=30)
    group_id: int
    subgroup_id: int | None = None
    active: bool = True


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    number: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=30)
    group_id: int | None = None
    subgroup_id: int | None = None
    active: bool | None = None


class StudentRead(ReadBase, StudentCreate):
    pass


def _validate_student(db, st: m.Student) -> None:
    clean_phone(db, st)
    if st.subgroup_id is not None:
        sg = db.get(m.Subgroup, st.subgroup_id)
        if sg is None or sg.group_id != st.group_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Kiçi topar talybyň toparyna degişli däl.")


students_router = APIRouter(prefix="/students", tags=["Talyplar"], dependencies=[Depends(require_staff)])


@students_router.post("/demo", dependencies=[Depends(require_admin)])
def create_demo(db: DbSession):
    """Talyby ýok toparlara synag talyplaryny (türkmen atlary bilen) döredýär."""
    return {"created": create_demo_students(db)}


router.include_router(build_crud_router(
    model=m.Student, create_schema=StudentCreate, update_schema=StudentUpdate, read_schema=StudentRead,
    prefix="/students", tag="Talyplar", filters=("group_id", "subgroup_id"), search_field="full_name",
    order_by=("group_id", "full_name"), validate=_validate_student, router=students_router, scope=sc.STUDENT,
))


# --- bahalar ---
class MarkIn(BaseModel):
    student_id: int
    value: m.MarkValue | None = None  # None — bahany aýyrmak


class LessonMarksIn(BaseModel):
    entry_id: int
    day: date
    marks: list[MarkIn]


def _lesson_out(db, user: m.User, les: j.Lesson, day: date) -> dict:
    marks = {mk.student_id: mk.value.value for mk in db.scalars(select(m.Mark).where(
        m.Mark.assignment_id == les.assignment.id, m.Mark.day == day, m.Mark.time_slot_id == les.slot.id))}
    groups = {g.id: g.name for g in db.scalars(select(m.Group).where(m.Group.id.in_(les.group_ids)))}
    subs = {s.id: s.name for s in db.scalars(select(m.Subgroup).where(m.Subgroup.group_id.in_(les.group_ids)))}
    return {
        "entry_id": les.entry.id, "assignment_id": les.assignment.id, "day": day.isoformat(),
        "starts_at": les.slot.starts_at.strftime("%H:%M"), "ends_at": les.slot.ends_at.strftime("%H:%M"),
        "subject": db.get(m.Subject, les.item.subject_id).name, "lesson_type": les.item.lesson_type.value,
        "groups": [groups[g] for g in les.group_ids if g in groups],
        "subgroup": subs.get(les.assignment.subgroup_id),
        "editable": j.editable(user, day), "deadline": j.deadline(day).isoformat(),
        "students": [{"id": s.id, "name": s.full_name, "group": groups.get(s.group_id), "mark": marks.get(s.id)}
                     for s in j.students(db, les)],
    }


def _own_lesson(db, user: m.User, entry_id: int) -> tuple[m.Timetable, j.Lesson]:
    tt = j.published_timetable(db)
    les = j.lesson(db, entry_id)
    if tt is None or les.entry.timetable_id != tt.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu sapak çap edilen raspisaniýede ýok.")
    if user.role != m.Role.admin and les.assignment.teacher_id != user.teacher_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu siziň sapagyňyz däl.")
    return tt, les


me = APIRouter(prefix="/me", tags=["Meniň raspisaniýäm"])


@me.get("/lesson")
def my_lesson(entry_id: int, day: date, user: TeacherUser, db: DbSession):
    """Sapagyň talyplary we şol günüň bahalary (`editable` — baha goýup bolýarmy)."""
    tt, les = _own_lesson(db, user, entry_id)
    j.check_day(tt, les, day)
    return _lesson_out(db, user, les, day)


@me.put("/lesson")
def save_my_lesson(payload: LessonMarksIn, user: TeacherUser, db: DbSession):
    tt, les = _own_lesson(db, user, payload.entry_id)
    j.check_day(tt, les, payload.day)
    if not j.editable(user, payload.day):
        msg = ("Sapak heniz bolmady." if payload.day > date.today()
               else f"Baha goýmak möhleti geçdi ({j.EDIT_DAYS} gün). Okuw bölümine ýüz tutuň.")
        raise HTTPException(status.HTTP_403_FORBIDDEN, msg)
    j.save_marks(db, user, les, payload.day, {x.student_id: x.value.value if x.value else None for x in payload.marks})
    return _lesson_out(db, user, les, payload.day)


@me.get("/courses")
def my_courses(user: TeacherUser, db: DbSession):
    """Mugallymyň çap edilen raspisaniýedäki sapaklary (žurnal saýlamak üçin)."""
    tt = j.published_timetable(db)
    if tt is None:
        return []
    ids = set(db.scalars(select(m.TimetableEntry.assignment_id).join(
        m.TeachingAssignment, m.TeachingAssignment.id == m.TimetableEntry.assignment_id).where(
        m.TimetableEntry.timetable_id == tt.id, m.TeachingAssignment.teacher_id == user.teacher_id)))
    return sorted((_course(db, db.get(m.TeachingAssignment, i)) for i in ids), key=lambda c: (c["subject"], c["groups"]))


def _course(db, a: m.TeachingAssignment) -> dict:
    item = db.get(m.CurriculumItem, a.curriculum_item_id)
    gids = [g.id for g in db.get(m.Stream, item.stream_id).groups] if item.stream_id else [item.group_id]
    names = {g.id: g.name for g in db.scalars(select(m.Group).where(m.Group.id.in_(gids)))}
    return {"assignment_id": a.id, "subject": db.get(m.Subject, item.subject_id).name,
            "lesson_type": item.lesson_type.value, "groups": ", ".join(names[g] for g in gids if g in names),
            "subgroup": db.get(m.Subgroup, a.subgroup_id).name if a.subgroup_id else None}


@me.get("/journal/{assignment_id}")
def my_journal(assignment_id: int, user: TeacherUser, db: DbSession):
    a = get_or_404(db, m.TeachingAssignment, assignment_id, "Sapak")
    if a.teacher_id != user.teacher_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu siziň sapagyňyz däl.")
    tt = j.published_timetable(db)
    if tt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Çap edilen raspisaniýe ýok.")
    return j.gradebook(db, tt, a)


router.include_router(me)

# --- admin: ähli žurnallar ---
admin = APIRouter(prefix="/journal", tags=["Žurnal"], dependencies=[Depends(require_staff)])  # dekan: öz fakulteti


@admin.get("/courses")
def group_courses(group_id: int, db: DbSession, fid: FacultyScope):
    """Toparyň çap edilen raspisaniýedäki sapaklary (potok sapaklary bilen)."""
    if fid is not None and sc.group_faculty(db, group_id) != fid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NOT_YOURS)
    tt = j.published_timetable(db)
    if tt is None:
        return []
    out = []
    ids = set(db.scalars(select(m.TimetableEntry.assignment_id).where(m.TimetableEntry.timetable_id == tt.id)))
    for a in db.scalars(select(m.TeachingAssignment).where(m.TeachingAssignment.id.in_(ids))):
        item = db.get(m.CurriculumItem, a.curriculum_item_id)
        gids = [g.id for g in db.get(m.Stream, item.stream_id).groups] if item.stream_id else [item.group_id]
        if group_id in gids:
            out.append({**_course(db, a), "teacher": db.get(m.Teacher, a.teacher_id).name})
    return sorted(out, key=lambda c: (c["subject"], c["lesson_type"], c["subgroup"] or ""))


@admin.get("/{assignment_id}")
def admin_journal(assignment_id: int, db: DbSession, fid: FacultyScope):
    a = get_or_404(db, m.TeachingAssignment, assignment_id, "Sapak")
    check_owner(sc.ASSIGNMENT, db, a, fid)
    tt = j.published_timetable(db)
    if tt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Çap edilen raspisaniýe ýok.")
    return j.gradebook(db, tt, a)


class AdminMarkIn(BaseModel):
    student_id: int
    day: date
    time_slot_id: int
    value: m.MarkValue | None = None


@admin.put("/{assignment_id}")
def admin_set_mark(assignment_id: int, payload: AdminMarkIn, user: CurrentUser, db: DbSession, fid: FacultyScope):
    """Admin (okuw bölümi) we dekan (öz fakulteti) islendik güne baha goýup ýa-da düzedip bilýär."""
    check_owner(sc.ASSIGNMENT, db, get_or_404(db, m.TeachingAssignment, assignment_id, "Sapak"), fid)
    tt = j.published_timetable(db)
    entry = db.scalar(select(m.TimetableEntry).where(
        m.TimetableEntry.timetable_id == tt.id, m.TimetableEntry.assignment_id == assignment_id,
        m.TimetableEntry.time_slot_id == payload.time_slot_id)) if tt else None
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sapak tapylmady.")
    les = j.lesson(db, entry.id)
    j.check_day(tt, les, payload.day)
    j.save_marks(db, user, les, payload.day, {payload.student_id: payload.value.value if payload.value else None})
    return {"ok": True}


router.include_router(admin)
