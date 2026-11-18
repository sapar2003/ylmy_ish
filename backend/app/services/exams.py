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


def other_sessions_busy(db: Session, session: m.ExamSession, slots: list) -> tuple[frozenset, frozenset, list]:
    """Şol günlere düşýän beýleki möwsümleriň (çap edilen, ýok bolsa iň soňky düzülen) tertibindäki
    mugallymlar we otaglar: (id, gün, wagt belgisi). Maslahat (synagdan öňki iş güni 08:30) hem hasaba alynýar."""
    number_of = {}  # (gün, başlanýan wagt) -> şu möwsümiň wagt belgisi
    for s in slots:
        p = next(pr for pr in session.periods if pr.id == s.period_id)
        number_of[s.day, p.starts_at] = s.number
    first = min((s.number for s in slots), default=1)
    days = sorted({s.day for s in slots})
    teachers, rooms, used = set(), set(), []
    others = db.scalars(select(m.ExamSession).where(
        m.ExamSession.id != session.id, m.ExamSession.starts_on <= session.ends_on,
        m.ExamSession.ends_on >= session.starts_on))
    for other in others:
        sch = (db.scalar(select(m.ExamSchedule).where(m.ExamSchedule.session_id == other.id,
                                                      m.ExamSchedule.published.is_(True))
                         .order_by(m.ExamSchedule.id.desc()))
               or db.scalar(select(m.ExamSchedule).where(m.ExamSchedule.session_id == other.id,
                                                         m.ExamSchedule.status == m.TimetableStatus.done)
                            .order_by(m.ExamSchedule.id.desc())))
        if sch is None:
            continue
        used.append(f"{other.name}: {sch.name}")
        other_days = exam_days(other)
        prev = {d: other_days[i - 1] for i, d in enumerate(other_days) if i}
        rows = db.execute(select(m.ExamEntry, m.Exam, m.ExamPeriod)
                          .join(m.Exam, m.Exam.id == m.ExamEntry.exam_id)
                          .join(m.ExamPeriod, m.ExamPeriod.id == m.ExamEntry.period_id)
                          .where(m.ExamEntry.schedule_id == sch.id)).all()
        for entry, exam, period in rows:
            n = number_of.get((entry.day, period.starts_at))
            for t in (exam.examiner_id, exam.assistant_id):
                if t is not None and n is not None:
                    teachers.add((t, entry.day, n))
            if entry.room_id is not None and n is not None:
                rooms.add((entry.room_id, entry.day, n))
            if other.consultations and entry.day in prev and prev[entry.day] in days:
                teachers.add((exam.examiner_id, prev[entry.day], first))
    return frozenset(teachers), frozenset(rooms), used


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
    compact = set(session.compact_group_ids or [])

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
        home = groups[group_ids[0]].home_room_id if len(group_ids) == 1 and e.room_type_id is None else None
        items.append(ExamItem(
            key=str(e.id), group_ids=tuple(group_ids), teacher_ids=teacher_ids, size=max(size, 1),
            room_type_id=e.room_type_id, faculty_ids=frozenset(faculty_of[g] for g in group_ids),
            label=f"{owner} · {subjects[e.subject_id].name} · {teachers[e.examiner_id].name}",
            examiner_id=e.examiner_id, fixed_room_id=home, compact=bool(compact) and set(group_ids) <= compact,
            weekdays=frozenset(e.weekdays) if e.weekdays else None, latest_day=e.latest_day,
        ))
    busy_t, busy_r, used = other_sessions_busy(db, session, slots)
    if used:
        warnings.append("Beýleki möwsümleriň synaglary hasaba alyndy (mugallym we otag çaknyşmasyn): " + ", ".join(used))
    # Öňki raspisaniýe (çap edilen, ýok bolsa iň soňky taýýary): synaglar mümkin boldugyça ýerinde galýar
    prev_sch = (db.scalar(select(m.ExamSchedule).where(m.ExamSchedule.session_id == session.id,
                                                       m.ExamSchedule.published.is_(True))
                          .order_by(m.ExamSchedule.id.desc()))
                or db.scalar(select(m.ExamSchedule).where(m.ExamSchedule.session_id == session.id,
                                                          m.ExamSchedule.status == m.TimetableStatus.done)
                             .order_by(m.ExamSchedule.id.desc())))
    previous = {}
    if prev_sch is not None:
        num = {p.id: p.number for p in session.periods}
        for en in db.scalars(select(m.ExamEntry).where(m.ExamEntry.schedule_id == prev_sch.id)):
            previous[str(en.exam_id)] = (en.day, num.get(en.period_id))
    rooms = solver_rooms(db)
    if session.own_rooms_only:  # umumy (fakultetsiz) otaglar ulanylmaýar
        rooms = [r for r in rooms if r.faculty_id is not None]
    inp = ExamInput(busy_teachers=busy_t, busy_rooms=busy_r, previous=previous,
        slots=slots, rooms=rooms, exams=items, max_per_day=session.max_per_day,
        rest_days=session.rest_days, consultations=session.consultations,
        spread_days=session.rest_days + 2 if session.consultations else 0, time_limit_seconds=time_limit_seconds,
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
            sch.archived = not result.ok  # şowsuz düzüliş sanawda görünmeýär
            sch.solver_status = result.status
            sch.issues = warnings + result.issues
            sch.objective = result.objective
            sch.seconds = round(result.seconds, 2)
        except Exception as exc:  # solweriň ýalňyşlygy API-ni ýykmaly däl
            log.exception("exam generation failed")
            db.rollback()
            sch = db.get(m.ExamSchedule, schedule_id)
            sch.status = m.TimetableStatus.failed
            sch.archived = True
            sch.issues = [f"Içki ýalňyşlyk: {exc}"]
        db.commit()


def start_exam_generation(session_factory: sessionmaker, schedule_id: int, background: bool = True) -> None:
    if background:
        threading.Thread(target=run_exam_generation, args=(session_factory, schedule_id), daemon=True).start()
    else:
        run_exam_generation(session_factory, schedule_id)
