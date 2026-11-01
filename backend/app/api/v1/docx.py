"""Raspisaniýeleri Word (.docx) görnüşinde ýüklemek."""
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel

from app import models as m
from app.api.crud import DbSession, get_or_404
from app.services.docx_export import DocOptions, exam_docx, timetable_docx
from app.services.exams import exam_days

router = APIRouter(tags=["Word"])

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DocQuery(BaseModel):
    page: list[str]  # her sahypa: toparlaryň id-leri otur bilen, meselem "1,2,3"
    mini: bool = False
    academic_year: str = DocOptions.academic_year
    semester: str = DocOptions.semester
    prorector: str = DocOptions.prorector
    rector: str = DocOptions.rector
    dean_title: str = DocOptions.dean_title
    dean: str = DocOptions.dean
    office_head: str = DocOptions.office_head


def _pages(q: DocQuery) -> list[list[int]]:
    try:
        pages = [[int(x) for x in page.split(",") if x.strip()] for page in q.page]
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "page: toparlaryň id-leri otur bilen bolmaly.")
    pages = [pg for pg in pages if pg]
    if not pages:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Iň az bir topar saýlaň.")
    return pages


def _options(q: DocQuery) -> DocOptions:
    return DocOptions(**q.model_dump(exclude={"page"}))


def _file(content: bytes, name: str) -> Response:
    return Response(content, media_type=DOCX, headers={
        "Content-Disposition": f"attachment; filename=\"raspisaniye.docx\"; filename*=UTF-8''{quote(name)}.docx",
    })


@router.get("/timetables/{timetable_id}/docx")
def timetable_word(timetable_id: int, db: DbSession, q: Annotated[DocQuery, Query()]):
    """Hepdelik raspisaniýe: her `page` aýry sahypa ("OKUW SAPAKLARYNYŇ TERTIBI")."""
    tt = get_or_404(db, m.Timetable, timetable_id, "Raspisaniýe")
    if tt.status != m.TimetableStatus.done:
        raise HTTPException(status.HTTP_409_CONFLICT, "Raspisaniýe heniz taýýar däl.")
    pages = _pages(q)
    names = {g.id: g.name for g in db.query(m.Group).filter(m.Group.id.in_({g for pg in pages for g in pg}))}
    title = "Raspisaniýe " + "; ".join(", ".join(names.get(g, "") for g in pg) for pg in pages[:3])
    return _file(timetable_docx(db, tt, pages, _options(q)), title[:120])


@router.get("/exam-schedules/{schedule_id}/docx")
def exam_word(schedule_id: int, db: DbSession, q: Annotated[DocQuery, Query()]):
    """Synag raspisaniýesi: her `page` aýry sahypa ("ARA SYNAGLARYŇ GÜN TERTIBI")."""
    sch = get_or_404(db, m.ExamSchedule, schedule_id, "Synag raspisaniýesi")
    if sch.status != m.TimetableStatus.done:
        raise HTTPException(status.HTTP_409_CONFLICT, "Synag raspisaniýesi heniz taýýar däl.")
    pages = _pages(q)
    session = db.get(m.ExamSession, sch.session_id)
    names = {g.id: g.name for g in db.query(m.Group).filter(m.Group.id.in_({g for pg in pages for g in pg}))}
    title = "Synag " + "; ".join(", ".join(names.get(g, "") for g in pg) for pg in pages[:3])
    return _file(exam_docx(db, sch, exam_days(session), pages, _options(q)), title[:120])
