from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import models as m
from app import solver as sv
from app.api.crud import DbSession, get_or_404
from app.core.config import settings
from app.db.session import get_session_factory
from app.schemas import timetable as s
from app.services.generation import build_input, start_generation

router = APIRouter(prefix="/timetables", tags=["Raspisaniýe"])


def _read(db: Session, tt: m.Timetable) -> s.TimetableRead:
    count = db.scalar(select(func.count()).where(m.TimetableEntry.timetable_id == tt.id))
    return s.TimetableRead.model_validate(tt).model_copy(update={"entry_count": count})


@router.get("/precheck", response_model=s.PrecheckRead)
def run_precheck(db: DbSession):
    """Raspisaniýe düzmezden öň maglumatlary barlaýar (solweri işletmeýär)."""
    inp, warnings = build_input(db, 0)
    return s.PrecheckRead(
        lessons=len(inp.lessons),
        lessons_per_week=sum(lesson.per_week for lesson in inp.lessons),
        issues=warnings + sv.precheck(inp),
    )


@router.post("", response_model=s.TimetableRead, status_code=status.HTTP_202_ACCEPTED)
def create_timetable(
    payload: s.TimetableCreate,
    db: DbSession,
    factory: Annotated[sessionmaker, Depends(get_session_factory)],
):
    """Täze raspisaniýe döredýär we fonda düzüp başlaýar. Ýagdaýyny `GET /timetables/{id}` bilen yzarlaň."""
    tt = m.Timetable(name=payload.name, time_limit_seconds=payload.time_limit_seconds, issues=[])
    db.add(tt)
    db.commit()
    start_generation(factory, tt.id, background=settings.generation_in_background)
    db.refresh(tt)
    return _read(db, tt)


@router.get("", response_model=list[s.TimetableRead])
def list_timetables(db: DbSession):
    return [_read(db, tt) for tt in db.scalars(select(m.Timetable).order_by(m.Timetable.id.desc()))]


@router.get("/{timetable_id}", response_model=s.TimetableRead)
def get_timetable(timetable_id: int, db: DbSession):
    return _read(db, get_or_404(db, m.Timetable, timetable_id, "Raspisaniýe"))


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable(timetable_id: int, db: DbSession):
    db.delete(get_or_404(db, m.Timetable, timetable_id, "Raspisaniýe"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{timetable_id}/entries", response_model=list[s.EntryRead])
def list_entries(
    timetable_id: int,
    db: DbSession,
    group_id: int | None = Query(None, description="Toparyň ähli sapaklary (potok we kiçi topar sapaklary bilen)"),
    teacher_id: int | None = None,
    room_id: int | None = None,
):
    get_or_404(db, m.Timetable, timetable_id, "Raspisaniýe")
    rows = db.execute(
        select(m.TimetableEntry, m.TeachingAssignment, m.CurriculumItem, m.TimeSlot)
        .join(m.TeachingAssignment, m.TeachingAssignment.id == m.TimetableEntry.assignment_id)
        .join(m.CurriculumItem, m.CurriculumItem.id == m.TeachingAssignment.curriculum_item_id)
        .join(m.TimeSlot, m.TimeSlot.id == m.TimetableEntry.time_slot_id)
        .where(m.TimetableEntry.timetable_id == timetable_id)
        .order_by(m.TimeSlot.weekday, m.TimeSlot.starts_at)
    ).all()

    names = lambda model: {o.id: o for o in db.scalars(select(model))}  # noqa: E731
    subjects, teachers, rooms = names(m.Subject), names(m.Teacher), names(m.Room)
    groups, subgroups, streams = names(m.Group), names(m.Subgroup), names(m.Stream)

    out = []
    for entry, a, item, slot in rows:
        stream = streams.get(item.stream_id) if item.stream_id else None
        group_ids = [g.id for g in stream.groups] if stream else [item.group_id]
        if group_id is not None and group_id not in group_ids:
            continue
        if teacher_id is not None and a.teacher_id != teacher_id:
            continue
        if room_id is not None and entry.room_id != room_id:
            continue
        room = rooms.get(entry.room_id) if entry.room_id else None
        sub = subgroups.get(a.subgroup_id) if a.subgroup_id else None
        out.append(s.EntryRead(
            id=entry.id, time_slot_id=slot.id, weekday=slot.weekday, number=slot.number,
            starts_at=slot.starts_at, ends_at=slot.ends_at,
            subject=s.Ref(id=item.subject_id, name=subjects[item.subject_id].name),
            lesson_type=item.lesson_type,
            teacher=s.Ref(id=a.teacher_id, name=teachers[a.teacher_id].name),
            room=s.Ref(id=room.id, name=room.name) if room else None,
            groups=[s.Ref(id=g, name=groups[g].name) for g in group_ids],
            subgroup=s.Ref(id=sub.id, name=sub.name) if sub else None,
            stream=s.Ref(id=stream.id, name=stream.name) if stream else None,
        ))
    return out
