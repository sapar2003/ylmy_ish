"""Sapagyň temasy we prezentasiýasy: mugallym goýýar, şol sapagy okaýan talyplar görýär we ýükleýär."""
import secrets
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.api.auth import CurrentUser, TeacherUser
from app.api.crud import DbSession, get_or_404
from app.api.v1.journal import _own_lesson
from app.core.config import settings
from app.schemas.topic import TopicRead
from app.services import convert, journal as j

router = APIRouter()

MAX_FILE_MB = 30
ALLOWED = {".pdf", ".ppt", ".pptx", ".pps", ".ppsx", ".odp", ".doc", ".docx", ".odt", ".xls", ".xlsx", ".txt",
           ".jpg", ".jpeg", ".png", ".zip"}


def topic_read(t: m.LessonTopic) -> TopicRead:
    url = f"/api/v1/public/files/{t.id}/{quote(t.file_name)}" if t.file_key and t.file_name else None
    preview = convert.preview_kind(t.file_name) if url else None
    return TopicRead(id=t.id, assignment_id=t.assignment_id, day=t.day, time_slot_id=t.time_slot_id, topic=t.topic,
                     note=t.note, file_name=t.file_name, file_size=t.file_size, file_url=url, preview=preview,
                     preview_url=f"/api/v1/public/preview/{t.id}" if preview else None)


def week_topics(db: Session, assignment_ids: set[int], week_start: date) -> list[TopicRead]:
    """Bu sapaklaryň şol hepdedäki (duşenbe – ýekşenbe) temalary."""
    if not assignment_ids:
        return []
    rows = db.scalars(select(m.LessonTopic).where(
        m.LessonTopic.assignment_id.in_(assignment_ids),
        m.LessonTopic.day >= week_start, m.LessonTopic.day <= week_start + timedelta(days=6)))
    return [topic_read(t) for t in rows]


def _upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _find(db: Session, les: j.Lesson, day: date) -> m.LessonTopic | None:
    return db.scalar(select(m.LessonTopic).where(
        m.LessonTopic.assignment_id == les.assignment.id, m.LessonTopic.day == day,
        m.LessonTopic.time_slot_id == les.slot.id))


def _lesson(db: Session, user: m.User, entry_id: int, day: date) -> j.Lesson:
    tt, les = _own_lesson(db, user, entry_id)
    j.check_day(tt, les, day)
    return les


def _remove_file(t: m.LessonTopic) -> None:
    if t.file_key:
        source = _upload_dir() / t.file_key
        source.unlink(missing_ok=True)
        convert.pdf_path(source).unlink(missing_ok=True)
    t.file_key = t.file_name = t.file_size = None


me = APIRouter(prefix="/me/topic", tags=["Sapagyň temasy"])


class TopicIn(BaseModel):
    entry_id: int
    day: date
    topic: str = Field(default="", max_length=300)
    note: str | None = Field(default=None, max_length=4000)


@me.get("", response_model=TopicRead | None)
def get_topic(entry_id: int, day: date, user: TeacherUser, db: DbSession):
    t = _find(db, _lesson(db, user, entry_id, day), day)
    return topic_read(t) if t else None


@me.put("", response_model=TopicRead | None)
def save_topic(payload: TopicIn, user: TeacherUser, db: DbSession):
    """Temany we belligi ýazýar; hemmesi boş we faýl ýok bolsa ýazgy aýrylýar."""
    les = _lesson(db, user, payload.entry_id, payload.day)
    t = _find(db, les, payload.day)
    topic, note = payload.topic.strip(), (payload.note or "").strip() or None
    if t is None:
        if not topic and not note:
            return None
        t = m.LessonTopic(assignment_id=les.assignment.id, day=payload.day, time_slot_id=les.slot.id)
        db.add(t)
    if not topic and not note and not t.file_key:
        db.delete(t)
        db.commit()
        return None
    t.topic, t.note, t.user_id = topic, note, user.id
    db.commit()
    return topic_read(t)


@me.put("/file", response_model=TopicRead)
async def upload_file(entry_id: int, day: date, name: str, request: Request, background: BackgroundTasks,
                      user: TeacherUser, db: DbSession):
    """Prezentasiýa (ýa-da başga faýl) ýüklemek: faýlyň özi sorag bedeninde, ady `name`-de.
    Öňki faýl bar bolsa çalşylýar."""
    les = _lesson(db, user, entry_id, day)
    name = Path(name).name.strip()[:200]
    ext = Path(name).suffix.lower()
    if not name or ext not in ALLOWED:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Bu görnüşdäki faýly goýup bolmaýar. Mysal: PDF, PowerPoint (pptx), Word (docx).")
    data = await request.body()
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Faýl boş.")
    if len(data) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"Faýl {MAX_FILE_MB} MB-dan uly bolmaly däl.")
    t = _find(db, les, day)
    if t is None:
        t = m.LessonTopic(assignment_id=les.assignment.id, day=day, time_slot_id=les.slot.id, topic="")
        db.add(t)
    _remove_file(t)
    key = f"{secrets.token_hex(16)}{ext}"
    (_upload_dir() / key).write_bytes(data)
    t.file_key, t.file_name, t.file_size, t.user_id = key, name, len(data), user.id
    db.commit()
    if ext in convert.CONVERTIBLE:  # talyp açanda garaşmaz ýaly öňünden öwrülýär
        background.add_task(convert.ensure_pdf, _upload_dir() / key)
    return topic_read(t)


@me.delete("/file", response_model=TopicRead | None)
def delete_file(entry_id: int, day: date, user: TeacherUser, db: DbSession):
    les = _lesson(db, user, entry_id, day)
    t = _find(db, les, day)
    if t is None:
        return None
    _remove_file(t)
    if not t.topic and not t.note:
        db.delete(t)
        db.commit()
        return None
    db.commit()
    return topic_read(t)


router.include_router(me)


@router.get("/public/files/{topic_id}/{name}", tags=["Talyplar üçin"])
def download(topic_id: int, name: str, _user: CurrentUser, db: DbSession):
    """Sapagyň faýlyny ýüklemek: brauzerden açylýar, şonuň üçin token ?token= bilen hem kabul edilýär."""
    t = get_or_404(db, m.LessonTopic, topic_id, "Faýl")
    path = _upload_dir() / t.file_key if t.file_key else None
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faýl tapylmady.")
    return FileResponse(path, filename=t.file_name)


@router.get("/public/preview/{topic_id}", tags=["Talyplar üçin"])
def preview(topic_id: int, _user: CurrentUser, db: DbSession):
    """App-yň içinde görkezmek üçin: PDF (gerek bolsa öwrülýär) ýa-da surat."""
    t = get_or_404(db, m.LessonTopic, topic_id, "Faýl")
    kind = convert.preview_kind(t.file_name)
    source = _upload_dir() / t.file_key if t.file_key else None
    if source is None or not source.is_file() or kind is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu faýly app-yň içinde görkezip bolmaýar.")
    if kind == "image":
        return FileResponse(source)
    pdf = convert.ensure_pdf(source)
    if pdf is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Faýly görkezmek üçin taýýarlap bolmady. Asyl faýly ýükläň.")
    return FileResponse(pdf, media_type="application/pdf")
