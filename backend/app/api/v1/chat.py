"""Mugallym bilen talybyň çaty. Talyp diňe özüne okadýan mugallymlara, mugallym diňe öz talyplaryna ýazyp bilýär
(çap edilen raspisaniýe boýunça); öňden söhbeti bar bolsa dowam etdirip bolýar."""
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.api.auth import CurrentUser
from app.api.crud import DbSession, get_or_404
from app.services import journal as j

router = APIRouter(prefix="/chat", tags=["Çat"])


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _role(user: m.User) -> str:
    if user.role == m.Role.teacher and user.teacher_id:
        return "teacher"
    if user.role == m.Role.student and user.student_id:
        return "student"
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Çat diňe mugallymlar we talyplar üçin.")


def _links(db: Session) -> list[tuple[int, list[int], int | None, str]]:
    """Çap edilen raspisaniýeden: (mugallym, toparlar, kiçi topar, ders ady)."""
    tt = j.published_timetable(db)
    if tt is None:
        return []
    ids = set(db.scalars(select(m.TimetableEntry.assignment_id).where(m.TimetableEntry.timetable_id == tt.id)))
    subjects = {s.id: s.name for s in db.scalars(select(m.Subject))}
    out = []
    for a in db.scalars(select(m.TeachingAssignment).where(m.TeachingAssignment.id.in_(ids))):
        item = db.get(m.CurriculumItem, a.curriculum_item_id)
        gids = [g.id for g in db.get(m.Stream, item.stream_id).groups] if item.stream_id else [item.group_id]
        out.append((a.teacher_id, gids, a.subgroup_id, subjects.get(item.subject_id, "")))
    return out


def _teaches(link: tuple, student: m.Student) -> bool:
    return student.group_id in link[1] and (link[2] is None or link[2] == student.subgroup_id)


def _contacts(db: Session, user: m.User) -> list[dict]:
    """Ýazyp boljak adamlar: talyba öz mugallymlary (dersleri bilen), mugallyma öz talyplary (topary bilen)."""
    links = _links(db)
    if _role(user) == "student":
        me = db.get(m.Student, user.student_id)
        subjects = defaultdict(set)
        for link in links:
            if _teaches(link, me):
                subjects[link[0]].add(link[3])
        teachers = db.scalars(select(m.Teacher).where(m.Teacher.id.in_(subjects)).order_by(m.Teacher.name))
        return [{"id": t.id, "name": t.name, "subtitle": ", ".join(sorted(subjects[t.id]))} for t in teachers]
    mine = [link for link in links if link[0] == user.teacher_id]
    group_ids = {g for link in mine for g in link[1]}
    groups = {g.id: g.name for g in db.scalars(select(m.Group).where(m.Group.id.in_(group_ids)))}
    students = db.scalars(select(m.Student).where(m.Student.group_id.in_(group_ids), m.Student.active.is_(True)))
    return sorted(({"id": s.id, "name": s.full_name, "subtitle": groups.get(s.group_id, "")}
                   for s in students if any(_teaches(link, s) for link in mine)),
                  key=lambda c: (c["subtitle"], c["name"]))


def _pair(user: m.User, other_id: int) -> tuple[int, int]:
    return (other_id, user.student_id) if _role(user) == "student" else (user.teacher_id, other_id)


def _thread(teacher_id: int, student_id: int):
    return m.ChatMessage.teacher_id == teacher_id, m.ChatMessage.student_id == student_id


def _check_allowed(db: Session, user: m.User, other_id: int) -> tuple[int, int]:
    teacher_id, student_id = _pair(user, other_id)
    if db.scalar(select(m.ChatMessage.id).where(*_thread(teacher_id, student_id)).limit(1)) is not None:
        return teacher_id, student_id  # öňden söhbet bar: dowam etdirip bolýar
    student = db.get(m.Student, student_id)
    if student is None or not any(link[0] == teacher_id and _teaches(link, student) for link in _links(db)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Diňe öz mugallymyňyz ýa-da talybyňyz bilen ýazyşyp bilersiňiz.")
    return teacher_id, student_id


def _time(value: datetime) -> str:
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()


def _read(msg: m.ChatMessage, role: str) -> dict:
    return {"id": msg.id, "text": msg.text, "mine": msg.sender == role, "at": _time(msg.created_at),
            "read": msg.read_at is not None}


@router.get("/contacts")
def contacts(user: CurrentUser, db: DbSession):
    return _contacts(db, user)


@router.get("/unread")
def unread(user: CurrentUser, db: DbSession):
    role = _role(user)
    column = m.ChatMessage.student_id == user.student_id if role == "student" else m.ChatMessage.teacher_id == user.teacher_id
    count = db.scalar(select(func.count()).where(column, m.ChatMessage.sender != role, m.ChatMessage.read_at.is_(None)))
    return {"count": count}


@router.get("/conversations")
def conversations(user: CurrentUser, db: DbSession):
    """Söhbetler: iň täzesi ýokarda, okalmadyk sany bilen."""
    role = _role(user)
    mine = m.ChatMessage.student_id == user.student_id if role == "student" else m.ChatMessage.teacher_id == user.teacher_id
    last, unread_count = {}, defaultdict(int)
    for msg in db.scalars(select(m.ChatMessage).where(mine).order_by(m.ChatMessage.id)):
        oid = msg.teacher_id if role == "student" else msg.student_id
        last[oid] = msg
        if msg.sender != role and msg.read_at is None:
            unread_count[oid] += 1
    subtitle = {c["id"]: c["subtitle"] for c in _contacts(db, user)}
    out = []
    for oid, msg in last.items():
        person = db.get(m.Teacher if role == "student" else m.Student, oid)
        name = person.name if role == "student" else person.full_name
        out.append({"id": oid, "name": name, "subtitle": subtitle.get(oid, ""), "last_text": msg.text,
                    "last_at": _time(msg.created_at), "last_mine": msg.sender == role, "unread": unread_count[oid],
                    "_order": msg.id})
    out.sort(key=lambda c: -c["_order"])
    for c in out:
        c.pop("_order")
    return out


@router.get("/{other_id}/messages")
def messages(other_id: int, user: CurrentUser, db: DbSession, after: int = 0):
    """Söhbetiň hatlary (`after`-den täzeleri); gelen hatlar okaldy diýlip bellenýär."""
    role = _role(user)
    teacher_id, student_id = _check_allowed(db, user, other_id)
    rows = list(db.scalars(select(m.ChatMessage).where(*_thread(teacher_id, student_id), m.ChatMessage.id > after)
                           .order_by(m.ChatMessage.id).limit(500)))
    now = datetime.now(UTC).replace(tzinfo=None)
    changed = False
    for msg in rows:
        if msg.sender != role and msg.read_at is None:
            msg.read_at, changed = now, True
    if changed:
        db.commit()
    return [_read(msg, role) for msg in rows]


@router.post("/{other_id}/messages", status_code=status.HTTP_201_CREATED)
def send(other_id: int, payload: MessageIn, user: CurrentUser, db: DbSession):
    role = _role(user)
    teacher_id, student_id = _check_allowed(db, user, other_id)
    get_or_404(db, m.Teacher, teacher_id, "Mugallym")
    get_or_404(db, m.Student, student_id, "Talyp")
    text = payload.text.strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Hat boş.")
    msg = m.ChatMessage(teacher_id=teacher_id, student_id=student_id, sender=role, text=text)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _read(msg, role)
