"""Synag möwsüminden solwer üçin giriş taýýarlaýar, solweri işledýär we netijäni ýazýar."""
import logging
import threading
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import models as m
from app.services.generation import group_faculties, solver_rooms
from app.solver.exams import ExamInput, ExamItem, ExamResult, ExamSlot, solve_exams

log = logging.getLogger(__name__)


def exam_days(session: m.ExamSession) -> list:
    days, d = [], session.starts_on
    while d <= session.ends_on:
        if d.isoweekday() in session.weekdays:
            days.append(d)
        d += timedelta(days=1)
    return days


def build_exam_input(db: Session, session: m.ExamSession, time_limit_seconds: float) -> tuple[ExamInput, list[str]]:
    warnings: list[str] = []
    slots, n = [], 0
    for day in exam_days(session):
        for p in session.periods:
            n += 1
            slots.append(ExamSlot(id=n, day=day, period_id=p.id, number=p.number))
    if not session.periods:
        warnings.append("Synag wagtlary ýok: möwsüme iň az bir wagt (meselem, 09:00-10:20) goşuň.")

    groups = {g.id: g for g in db.scalars(select(m.Group))}
    streams = {s.id: s for s in db.scalars(select(m.Stream))}
    subjects = {s.id: s for s in db.scalars(select(m.Subject))}
    teachers = {t.id: t for t in db.scalars(select(m.Teacher))}
    faculty_of = group_faculties(db)

    items = []
    for e in db.scalars(select(m.Exam).where(m.Exam.session_id == session.id).order_by(m.Exam.id)):
        if e.stream_id is not None:
            group_ids = [g.id for g in streams[e.stream_id].groups]
            owner = streams[e.stream_id].name
        else:
            group_ids = [e.group_id]
            owner = groups[e.group_id].name
        size = sum(groups[g].student_count for g in group_ids)
        teacher_ids = tuple(t for t in (e.examiner_id, e.assistant_id) if t is not None)
        items.append(ExamItem(
            key=str(e.id), group_ids=tuple(group_ids), teacher_ids=teacher_ids, size=max(size, 1),
            room_type_id=e.room_type_id, faculty_ids=frozenset(faculty_of[g] for g in group_ids),
            label=f"{owner} · {subjects[e.subject_id].name} · {teachers[e.examiner_id].name}",
        ))
    inp = ExamInput(
        slots=slots, rooms=solver_rooms(db), exams=items, max_per_day=session.max_per_day,
        rest_days=session.rest_days, time_limit_seconds=time_limit_seconds,
    )
    return inp, warnings


def run_exam_generation(session_factory: sessionmaker, schedule_id: int) -> None:
    with session_factory() as db:
        sch = db.get(m.ExamSchedule, schedule_id)
        sch.status = m.TimetableStatus.running
        db.commit()
        try:
            session = db.get(m.ExamSession, sch.session_id)
            inp, warnings = build_exam_input(db, session, sch.time_limit_seconds)
            if not inp.exams:
                result = ExamResult(ok=False, status="empty", issues=["Bu möwsümde synag ýok."])
            else:
                result = solve_exams(inp)
            if result.ok:
                slot_by_id = {s.id: s for s in inp.slots}
                db.add_all(
                    m.ExamEntry(
                        schedule_id=sch.id, exam_id=int(p.exam_key), day=slot_by_id[p.slot_id].day,
                        period_id=slot_by_id[p.slot_id].period_id, room_id=p.room_id,
                    )
                    for p in result.placements
                )
            sch.status = m.TimetableStatus.done if result.ok else m.TimetableStatus.failed
            sch.solver_status = result.status
            sch.issues = warnings + result.issues
            sch.objective = result.objective
            sch.seconds = round(result.seconds, 2)
        except Exception as exc:  # solweriň ýalňyşlygy API-ni ýykmaly däl
            log.exception("exam generation failed")
            db.rollback()
            sch = db.get(m.ExamSchedule, schedule_id)
            sch.status = m.TimetableStatus.failed
            sch.issues = [f"Içki ýalňyşlyk: {exc}"]
        db.commit()


def start_exam_generation(session_factory: sessionmaker, schedule_id: int, background: bool = True) -> None:
    if background:
        threading.Thread(target=run_exam_generation, args=(session_factory, schedule_id), daemon=True).start()
    else:
        run_exam_generation(session_factory, schedule_id)
