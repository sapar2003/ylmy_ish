"""Gündelik bahalar: sapagyň talyplary, sapak günleri, baha goýmak möhleti we žurnal tablisasy."""
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m

EDIT_DAYS = 3  # mugallym sapakdan soň şunça günüň dowamynda baha goýup/üýtgedip bilýär
DEFAULT_SEMESTER_START = date(2026, 9, 1)


@dataclass
class Lesson:
    entry: m.TimetableEntry
    assignment: m.TeachingAssignment
    item: m.CurriculumItem
    slot: m.TimeSlot
    group_ids: list[int]


def published_timetable(db: Session) -> m.Timetable | None:
    return db.scalar(select(m.Timetable).where(m.Timetable.published.is_(True)))


def week_of(tt: m.Timetable, day: date) -> int | None:
    if tt.weeks != 2:
        return None
    start = tt.starts_on or DEFAULT_SEMESTER_START
    first_monday = start - timedelta(days=start.weekday())
    return (day - first_monday).days // 7 % 2 + 1


def lesson(db: Session, entry_id: int) -> Lesson:
    entry = db.get(m.TimetableEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sapak tapylmady.")
    a = db.get(m.TeachingAssignment, entry.assignment_id)
    item = db.get(m.CurriculumItem, a.curriculum_item_id)
    groups = [g.id for g in db.get(m.Stream, item.stream_id).groups] if item.stream_id else [item.group_id]
    return Lesson(entry, a, item, db.get(m.TimeSlot, entry.time_slot_id), groups)


def check_day(tt: m.Timetable, les: Lesson, day: date) -> None:
    """Sapak şol gün hakykatdan bolýarmy: hepde güni, sanawjy/maýdalawjy hepde, ýarymýylyň seneleri."""
    if day.isoweekday() != les.slot.weekday:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bu sapak şol gün ýok (hepde güni gabat gelmeýär).")
    if les.entry.week is not None and week_of(tt, day) != les.entry.week:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bu sapak şol hepde ýok (sanawjy/maýdalawjy).")
    if (tt.starts_on and day < tt.starts_on) or (tt.ends_on and day > tt.ends_on):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Sene ýarymýylyň daşynda.")


def deadline(day: date) -> date:
    return day + timedelta(days=EDIT_DAYS)


def editable(user: m.User, day: date, today: date | None = None) -> bool:
    """Admin islendik wagt; mugallym — sapak güni we ondan soň EDIT_DAYS günüň dowamynda."""
    if user.role == m.Role.admin:
        return True
    today = today or date.today()
    return day <= today <= deadline(day)


def students(db: Session, les_or_assignment, group_ids: list[int] | None = None) -> list[m.Student]:
    """Sapagyň talyplary: kiçi topara bölünýän sapakda diňe şol kiçi topar, ýogsam toparlar (potok)."""
    a = les_or_assignment.assignment if isinstance(les_or_assignment, Lesson) else les_or_assignment
    gids = les_or_assignment.group_ids if isinstance(les_or_assignment, Lesson) else group_ids
    stmt = select(m.Student).join(m.Group, m.Group.id == m.Student.group_id).where(m.Student.active.is_(True))
    stmt = stmt.where(m.Student.subgroup_id == a.subgroup_id) if a.subgroup_id else stmt.where(m.Student.group_id.in_(gids))
    groups = {g.id: g.name for g in db.scalars(select(m.Group))}
    return sorted(db.scalars(stmt), key=lambda s: (groups.get(s.group_id, ""), tk_key(s.full_name)))


TK_ALPHABET = "abçdeäfghijžklmnňoöprsştuüwyýz"  # türkmen elipbiýiniň tertibi


def tk_key(text: str) -> list[int]:
    """Türkmen elipbiýi boýunça tertiplemek üçin (Ç - B-den soň, Ä - E-den soň, Ö - O-dan soň)."""
    return [TK_ALPHABET.find(ch) if ch in TK_ALPHABET else 100 + ord(ch) for ch in text.lower()]


def save_marks(db: Session, user: m.User, les: Lesson, day: date, values: dict[int, str | None]) -> int:
    """Bahalary ýazýar (None — aýyrmak); üýtgän her bahany MarkLog-a ýazýar. Üýtgän bahalaryň sanyny gaýtarýar."""
    allowed = {s.id for s in students(db, les)}
    bad = set(values) - allowed
    if bad:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Käbir talyplar bu sapaga degişli däl.")
    existing = {mk.student_id: mk for mk in db.scalars(select(m.Mark).where(
        m.Mark.assignment_id == les.assignment.id, m.Mark.day == day, m.Mark.time_slot_id == les.slot.id))}
    changed = 0
    for sid, value in values.items():
        old = existing.get(sid)
        old_value = old.value.value if old else None
        if old_value == value:
            continue
        if value is None:
            db.delete(old)
        elif old:
            old.value, old.user_id = m.MarkValue(value), user.id
        else:
            db.add(m.Mark(assignment_id=les.assignment.id, student_id=sid, day=day, time_slot_id=les.slot.id,
                          value=m.MarkValue(value), user_id=user.id))
        db.add(m.MarkLog(assignment_id=les.assignment.id, student_id=sid, day=day, time_slot_id=les.slot.id,
                         old_value=old_value, new_value=value, user_id=user.id))
        changed += 1
    db.commit()
    return changed


def lesson_days(tt: m.Timetable, entries: list[m.TimetableEntry], slots: dict[int, m.TimeSlot],
                until: date) -> list[tuple[date, m.TimeSlot]]:
    """Ýarymýylyň başyndan `until` çenli bu sapaklaryň bolan günleri (sene, slot)."""
    start = tt.starts_on or DEFAULT_SEMESTER_START
    end = min(until, tt.ends_on) if tt.ends_on else until
    out = []
    d = start
    while d <= end:
        for e in entries:
            s = slots[e.time_slot_id]
            if d.isoweekday() == s.weekday and (e.week is None or week_of(tt, d) == e.week):
                out.append((d, s))
        d += timedelta(days=1)
    return sorted(out, key=lambda x: (x[0], x[1].starts_at))


def gradebook(db: Session, tt: m.Timetable, assignment: m.TeachingAssignment, until: date | None = None) -> dict:
    """Žurnal: talyplar × sapak günleri, bahalar we her talybyň ortaça bahasy, gatnaşmazlyk sany."""
    item = db.get(m.CurriculumItem, assignment.curriculum_item_id)
    group_ids = [g.id for g in db.get(m.Stream, item.stream_id).groups] if item.stream_id else [item.group_id]
    entries = list(db.scalars(select(m.TimetableEntry).where(
        m.TimetableEntry.timetable_id == tt.id, m.TimetableEntry.assignment_id == assignment.id)))
    slots = {s.id: s for s in db.scalars(select(m.TimeSlot))}
    days = lesson_days(tt, entries, slots, until or date.today())
    studs = students(db, assignment, group_ids)
    marks = {(mk.student_id, mk.day, mk.time_slot_id): mk.value.value for mk in db.scalars(
        select(m.Mark).where(m.Mark.assignment_id == assignment.id))}
    groups = {g.id: g.name for g in db.scalars(select(m.Group).where(m.Group.id.in_(group_ids)))}
    rows = []
    for st in studs:
        vals = [marks.get((st.id, d, s.id)) for d, s in days]
        nums = [int(v) for v in vals if v and v != "gm"]
        rows.append({
            "student": {"id": st.id, "name": st.full_name}, "group": groups.get(st.group_id),
            "marks": vals, "average": round(sum(nums) / len(nums), 2) if nums else None,
            "absent": sum(1 for v in vals if v == "gm"),
        })
    subject = db.get(m.Subject, item.subject_id)
    return {
        "assignment_id": assignment.id, "subject": subject.name, "lesson_type": item.lesson_type.value,
        "groups": [groups[g] for g in group_ids if g in groups],
        "subgroup": db.get(m.Subgroup, assignment.subgroup_id).name if assignment.subgroup_id else None,
        "teacher": db.get(m.Teacher, assignment.teacher_id).name,
        "columns": [{"day": d.isoformat(), "time_slot_id": s.id, "starts_at": s.starts_at.strftime("%H:%M")}
                    for d, s in days],
        "rows": rows,
    }
