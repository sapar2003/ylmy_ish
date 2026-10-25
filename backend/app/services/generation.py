"""Maglumat bazasyndan solwer üçin giriş taýýarlaýar, solweri işledýär we netijäni ýazýar."""
import logging
import threading
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import models as m
from app import solver as sv

log = logging.getLogger(__name__)

LESSON_TYPE_NAMES = {"lecture": "leksiýa", "practice": "amaly", "lab": "tejribe", "seminar": "seminar"}


def group_faculties(db: Session) -> dict[int, int]:
    """topar id -> fakultet id (hünär -> kafedra -> fakultet arkaly)."""
    rows = db.execute(
        select(m.Group.id, m.Department.faculty_id)
        .join(m.Specialty, m.Specialty.id == m.Group.specialty_id)
        .join(m.Department, m.Department.id == m.Specialty.department_id)
    )
    return {group_id: faculty_id for group_id, faculty_id in rows}


def solver_rooms(db: Session) -> list[sv.Room]:
    return [
        sv.Room(id=r.id, capacity=r.capacity, room_type_id=r.room_type_id, faculty_id=r.faculty_id)
        for r in db.scalars(select(m.Room))
    ]


def build_input(db: Session, time_limit_seconds: float, weeks: int = 1) -> tuple[sv.SolverInput, list[str]]:
    """Solwer girişini we solwere girip bilmeýän ýazgylar barada duýduryşlary gaýtarýar."""
    warnings: list[str] = []
    slots = db.scalars(select(m.TimeSlot)).all()
    slots_by_shift: dict[int, set[int]] = defaultdict(set)
    for s in slots:
        slots_by_shift[s.shift_id].add(s.id)
    all_slots = frozenset(s.id for s in slots)

    groups = {g.id: g for g in db.scalars(select(m.Group))}
    faculty_of = group_faculties(db)
    subgroups = {s.id: s for s in db.scalars(select(m.Subgroup))}
    subgroups_of: dict[int, list[int]] = defaultdict(list)
    for s in subgroups.values():
        subgroups_of[s.group_id].append(s.id)
    streams = {s.id: s for s in db.scalars(select(m.Stream))}
    subjects = {s.id: s for s in db.scalars(select(m.Subject))}

    avail = defaultdict(lambda: {"unavailable": set(), "preferred": set()})
    for a in db.scalars(select(m.TeacherAvailability)):
        if a.status != m.AvailabilityStatus.available:
            avail[a.teacher_id][a.status.value].add(a.time_slot_id)
    teachers = {
        t.id: sv.Teacher(
            id=t.id, name=t.name, max_per_day=t.max_lessons_per_day, max_per_week=t.max_lessons_per_week,
            unavailable=frozenset(avail[t.id]["unavailable"]), preferred=frozenset(avail[t.id]["preferred"]),
        )
        for t in db.scalars(select(m.Teacher))
    }

    def group_slots(group_ids: list[int]) -> frozenset[int]:
        allowed = set(all_slots)
        for gid in group_ids:
            shift_id = groups[gid].shift_id
            if shift_id is not None:
                allowed &= slots_by_shift[shift_id]
        return frozenset(allowed)

    lessons: list[sv.Lesson] = []
    for item in db.scalars(select(m.CurriculumItem)):
        if item.stream_id is not None:
            stream = streams[item.stream_id]
            group_ids = [g.id for g in stream.groups]
            owner = stream.name
        else:
            group_ids = [item.group_id]
            owner = groups[item.group_id].name
        title = f"{owner} · {subjects[item.subject_id].name} ({LESSON_TYPE_NAMES[item.lesson_type.value]})"
        if not item.assignments:
            warnings.append(f"{title}: mugallym bellenmedik, raspisaniýä goşulmady.")
            continue
        if item.split:
            missing = set(subgroups_of[item.group_id]) - {a.subgroup_id for a in item.assignments}
            if missing:
                names = ", ".join(subgroups[s].name for s in sorted(missing))
                warnings.append(f"{title}: {names} kiçi topar(lar)a mugallym bellenmedik.")
        for a in item.assignments:
            if a.subgroup_id is not None:
                size = subgroups[a.subgroup_id].student_count
                label = f"{title}, {subgroups[a.subgroup_id].name}-nji kiçi topar · {teachers[a.teacher_id].name}"
            else:
                size = sum(groups[g].student_count for g in group_ids)
                label = f"{title} · {teachers[a.teacher_id].name}"
            lessons.append(sv.Lesson(
                key=str(a.id), curriculum_item_id=item.id, assignment_id=a.id, teacher_id=a.teacher_id,
                group_ids=tuple(group_ids), subgroup_id=a.subgroup_id, per_week=item.lessons_per_week, biweekly=item.biweekly,
                size=max(size, 1), room_type_id=item.room_type_id, allowed_slots=group_slots(group_ids),
                label=label, faculty_ids=frozenset(faculty_of[g] for g in group_ids),
            ))

    rooms = solver_rooms(db)
    if not slots:
        warnings.append("Wagt slotlary ýok: ilki smenalar üçin slotlary dörediň.")
    if not rooms:
        warnings.append("Otag ýok: ilki otaglary goşuň.")
    inp = sv.SolverInput(
        slots=[sv.Slot(s.id, s.weekday, s.number, s.shift_id) for s in slots],
        rooms=rooms, teachers=teachers, lessons=lessons, subgroups_of=dict(subgroups_of),
        time_limit_seconds=time_limit_seconds, weeks=weeks,
    )
    return inp, warnings


def run_generation(session_factory: sessionmaker, timetable_id: int) -> None:
    with session_factory() as db:
        tt = db.get(m.Timetable, timetable_id)
        tt.status = m.TimetableStatus.running
        db.commit()
        try:
            inp, warnings = build_input(db, tt.time_limit_seconds, tt.weeks)
            if not inp.lessons:
                result = sv.SolverResult(ok=False, status="empty", issues=["Okuw meýilnamasynda sapak ýok."])
            else:
                result = sv.solve(inp)
            if result.ok:
                db.add_all(
                    m.TimetableEntry(
                        timetable_id=tt.id, assignment_id=int(p.lesson_key), time_slot_id=p.slot_id, room_id=p.room_id,
                        week=p.week,
                    )
                    for p in result.placements
                )
            tt.status = m.TimetableStatus.done if result.ok else m.TimetableStatus.failed
            tt.solver_status = result.status
            tt.issues = warnings + result.issues
            tt.objective = result.objective
            tt.seconds = round(result.seconds, 2)
        except Exception as exc:  # solweriň ýalňyşlygy API-ni ýykmaly däl
            log.exception("generation failed")
            db.rollback()
            tt = db.get(m.Timetable, timetable_id)
            tt.status = m.TimetableStatus.failed
            tt.issues = [f"Içki ýalňyşlyk: {exc}"]
        db.commit()


def start_generation(session_factory: sessionmaker, timetable_id: int, background: bool = True) -> None:
    if background:
        threading.Thread(target=run_generation, args=(session_factory, timetable_id), daemon=True).start()
    else:
        run_generation(session_factory, timetable_id)
