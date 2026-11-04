"""Talyplar üçin (girişsiz): toparyny saýlap, çap edilen raspisaniýäni we synaglary görýär.

Diňe "Mugallymlara çap et" edilen raspisaniýe we synag raspisaniýesi görkezilýär; şahsy maglumat (baha, talyp
sanawy) bu ýerde ýok.
"""
from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import select

from app import models as m
from app.api.crud import DbSession, get_or_404
from app.api.v1.exams import list_entries as exam_entries
from app.api.v1.timetables import list_entries as timetable_entries
from app.api.v1.timetables import week_of
from app.schemas import user as s
from app.schemas.timetable import Ref

router = APIRouter(prefix="/public", tags=["Talyplar üçin"])


@router.get("/groups")
def groups(db: DbSession):
    """Ähli toparlar fakulteti we kiçi toparlary bilen (talyp öz toparyny saýlar ýaly)."""
    specs = {sp.id: sp for sp in db.scalars(select(m.Specialty))}
    deps = {d.id: d for d in db.scalars(select(m.Department))}
    facs = {f.id: f for f in db.scalars(select(m.Faculty))}
    out = []
    for g in db.scalars(select(m.Group).order_by(m.Group.course, m.Group.name)):
        dep = deps.get(specs[g.specialty_id].department_id) if g.specialty_id in specs else None
        fac = facs.get(dep.faculty_id) if dep else None
        out.append({"id": g.id, "name": g.name, "course": g.course,
                    "faculty": (fac.short_name or fac.name) if fac else None,
                    "subgroups": [{"id": sg.id, "name": sg.name} for sg in sorted(g.subgroups, key=lambda x: x.name)]})
    return out


@router.get("/timetable", response_model=s.MyWeekRead)
def group_timetable(group_id: int, db: DbSession, subgroup_id: int | None = None, on: date | None = None):
    """Toparyň (we kiçi toparynyň) çap edilen raspisaniýesi; `on` senäniň hepdesi (sanawjy/maýdalawjy)."""
    get_or_404(db, m.Group, group_id, "Topar")
    tt = db.scalar(select(m.Timetable).where(m.Timetable.published.is_(True)))
    if tt is None:
        return s.MyWeekRead(timetable=None)
    on = on or date.today()
    week = week_of(tt, on)
    entries = [e for e in timetable_entries(tt.id, db, group_id=group_id, teacher_id=None, room_id=None, week=week,
                                            on=None)
               if subgroup_id is None or e.subgroup is None or e.subgroup.id == subgroup_id]
    return s.MyWeekRead(timetable=Ref(id=tt.id, name=tt.name), weeks=tt.weeks, week=week,
                        week_start=on - timedelta(days=on.weekday()), entries=entries)


@router.get("/exams", response_model=list[s.MyExamRead])
def group_exams(group_id: int, db: DbSession):
    """Toparyň çap edilen synaglary (`partner` — synagy alýan uly mugallym)."""
    get_or_404(db, m.Group, group_id, "Topar")
    out = []
    for sch in db.scalars(select(m.ExamSchedule).where(m.ExamSchedule.published.is_(True))):
        session = db.get(m.ExamSession, sch.session_id)
        for e in exam_entries(sch.id, db, group_id=group_id, teacher_id=None, room_id=None):
            out.append(s.MyExamRead(
                schedule=Ref(id=sch.id, name=sch.name), session=Ref(id=session.id, name=session.name),
                kind=session.kind.value, day=e.day, starts_at=e.starts_at.strftime("%H:%M"),
                ends_at=e.ends_at.strftime("%H:%M"), subject=e.subject, role="student",
                groups=e.groups, room=e.room, partner=e.examiner,
            ))
    return sorted(out, key=lambda x: (x.day, x.starts_at))
