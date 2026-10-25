from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import models as m
from app.api.crud import DbSession, build_crud_router, get_or_404
from app.core.config import settings
from app.db.session import get_session_factory
from app.schemas import exam as s
from app.schemas.timetable import Ref
from app.services.exams import build_exam_input, exam_days, start_exam_generation
from app.solver.exams import exam_precheck

router = APIRouter()


def _invalid(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


def validate_exam(db: Session, exam: m.Exam) -> None:
    if (exam.group_id is None) == (exam.stream_id is None):
        raise _invalid("group_id ýa-da stream_id: diňe biri görkezilmeli.")
    if exam.assistant_id is not None and exam.assistant_id == exam.examiner_id:
        raise _invalid("Uly we kiçi mugallym dürli adam bolmaly.")


router.include_router(build_crud_router(
    model=m.ExamSession, create_schema=s.ExamSessionCreate, update_schema=s.ExamSessionUpdate,
    read_schema=s.ExamSessionRead, prefix="/exam-sessions", tag="Synag möwsümleri", order_by=("starts_on", "name"),
))
router.include_router(build_crud_router(
    model=m.ExamPeriod, create_schema=s.ExamPeriodCreate, update_schema=s.ExamPeriodUpdate,
    read_schema=s.ExamPeriodRead, prefix="/exam-periods", tag="Synag wagtlary", filters=("session_id",),
    search_field=None, order_by=("session_id", "number"),
))
router.include_router(build_crud_router(
    model=m.Exam, create_schema=s.ExamCreate, update_schema=s.ExamUpdate, read_schema=s.ExamRead,
    prefix="/exams", tag="Synaglar",
    filters=("session_id", "group_id", "stream_id", "subject_id", "examiner_id", "assistant_id"),
    search_field=None, order_by=("session_id", "id"), validate=validate_exam,
))

schedules = APIRouter(prefix="/exam-schedules", tags=["Synag raspisaniýesi"])


def _read(db: Session, sch: m.ExamSchedule) -> s.ExamScheduleRead:
    count = db.scalar(select(func.count()).where(m.ExamEntry.schedule_id == sch.id))
    return s.ExamScheduleRead.model_validate(sch).model_copy(update={"entry_count": count})


@schedules.get("/precheck", response_model=s.ExamPrecheckRead)
def run_precheck(session_id: int, db: DbSession):
    """Synag raspisaniýesini düzmezden öň maglumatlary barlaýar (solweri işletmeýär)."""
    session = get_or_404(db, m.ExamSession, session_id, "Synag möwsümi")
    inp, warnings = build_exam_input(db, session, 0)
    return s.ExamPrecheckRead(
        exams=len(inp.exams), days=len(exam_days(session)), slots=len(inp.slots),
        issues=warnings + exam_precheck(inp),
    )


@schedules.post("", response_model=s.ExamScheduleRead, status_code=status.HTTP_202_ACCEPTED)
def create_schedule(
    payload: s.ExamScheduleCreate,
    db: DbSession,
    factory: Annotated[sessionmaker, Depends(get_session_factory)],
):
    """Täze synag raspisaniýesini döredýär we fonda düzüp başlaýar."""
    get_or_404(db, m.ExamSession, payload.session_id, "Synag möwsümi")
    sch = m.ExamSchedule(**payload.model_dump(), issues=[])
    db.add(sch)
    db.commit()
    start_exam_generation(factory, sch.id, background=settings.generation_in_background)
    db.refresh(sch)
    return _read(db, sch)


@schedules.get("", response_model=list[s.ExamScheduleRead])
def list_schedules(db: DbSession, session_id: int | None = None):
    stmt = select(m.ExamSchedule).order_by(m.ExamSchedule.id.desc())
    if session_id is not None:
        stmt = stmt.where(m.ExamSchedule.session_id == session_id)
    return [_read(db, sch) for sch in db.scalars(stmt)]


@schedules.get("/{schedule_id}", response_model=s.ExamScheduleRead)
def get_schedule(schedule_id: int, db: DbSession):
    return _read(db, get_or_404(db, m.ExamSchedule, schedule_id, "Synag raspisaniýesi"))


@schedules.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: DbSession):
    db.delete(get_or_404(db, m.ExamSchedule, schedule_id, "Synag raspisaniýesi"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@schedules.get("/{schedule_id}/entries", response_model=list[s.ExamEntryRead])
def list_entries(
    schedule_id: int,
    db: DbSession,
    group_id: int | None = Query(None, description="Toparyň ähli synaglary (potok synaglary bilen)"),
    teacher_id: int | None = Query(None, description="Mugallymyň uly ýa-da kiçi mugallym bolan synaglary"),
    room_id: int | None = None,
):
    get_or_404(db, m.ExamSchedule, schedule_id, "Synag raspisaniýesi")
    rows = db.execute(
        select(m.ExamEntry, m.Exam, m.ExamPeriod)
        .join(m.Exam, m.Exam.id == m.ExamEntry.exam_id)
        .join(m.ExamPeriod, m.ExamPeriod.id == m.ExamEntry.period_id)
        .where(m.ExamEntry.schedule_id == schedule_id)
        .order_by(m.ExamEntry.day, m.ExamPeriod.number)
    ).all()

    names = lambda model: {o.id: o for o in db.scalars(select(model))}  # noqa: E731
    subjects, teachers, rooms = names(m.Subject), names(m.Teacher), names(m.Room)
    groups, streams = names(m.Group), names(m.Stream)
    ref = lambda o: Ref(id=o.id, name=o.name) if o else None  # noqa: E731

    out = []
    for entry, exam, period in rows:
        stream = streams.get(exam.stream_id) if exam.stream_id else None
        group_ids = [g.id for g in stream.groups] if stream else [exam.group_id]
        if group_id is not None and group_id not in group_ids:
            continue
        if teacher_id is not None and teacher_id not in (exam.examiner_id, exam.assistant_id):
            continue
        if room_id is not None and entry.room_id != room_id:
            continue
        out.append(s.ExamEntryRead(
            id=entry.id, exam_id=exam.id, day=entry.day, weekday=entry.day.isoweekday(), period=period.number,
            starts_at=period.starts_at, ends_at=period.ends_at,
            subject=ref(subjects[exam.subject_id]), examiner=ref(teachers[exam.examiner_id]),
            assistant=ref(teachers.get(exam.assistant_id)), room=ref(rooms.get(entry.room_id)),
            groups=[ref(groups[g]) for g in group_ids], stream=ref(stream),
        ))
    return out


router.include_router(schedules)
