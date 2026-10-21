from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.api.crud import build_crud_router
from app.schemas import curriculum as s

router = APIRouter()


def _invalid(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


def apply_stream(db: Session, stream: m.Stream, data: dict[str, Any]) -> None:
    group_ids = data.pop("group_ids", None)
    for key, value in data.items():
        setattr(stream, key, value)
    if group_ids is not None:
        if len(set(group_ids)) != len(group_ids):
            raise _invalid("Potokda bir topar iki gezek görkezilipdir.")
        groups = db.scalars(select(m.Group).where(m.Group.id.in_(group_ids))).all()
        if len(groups) != len(group_ids):
            raise _invalid("Käbir toparlar tapylmady.")
        stream.groups = list(groups)


def validate_curriculum_item(db: Session, item: m.CurriculumItem) -> None:
    if (item.group_id is None) == (item.stream_id is None):
        raise _invalid("group_id ýa-da stream_id: diňe biri görkezilmeli.")
    if item.split and item.group_id is None:
        raise _invalid("Diňe bir toparyň sapagy kiçi toparlara bölünip bilýär (potok däl).")
    if item.split:
        has_subgroups = db.scalar(select(m.Subgroup.id).where(m.Subgroup.group_id == item.group_id).limit(1))
        if has_subgroups is None:
            raise _invalid("Bu toparda kiçi topar ýok: ilki kiçi toparlary goşuň.")


def validate_assignment(db: Session, a: m.TeachingAssignment) -> None:
    item = db.get(m.CurriculumItem, a.curriculum_item_id)
    if item is None:
        raise _invalid("Okuw meýilnamasynyň ýazgysy tapylmady.")
    if not item.split:
        if a.subgroup_id is not None:
            raise _invalid("Bu sapak bölünmeýär: subgroup_id görkezilmeli däl.")
        other = db.scalar(
            select(m.TeachingAssignment.id).where(
                m.TeachingAssignment.curriculum_item_id == item.id, m.TeachingAssignment.id != a.id
            )
        ) if a.id else db.scalar(
            select(m.TeachingAssignment.id).where(m.TeachingAssignment.curriculum_item_id == item.id)
        )
        if other is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Bu sapaga eýýäm mugallym bellenipdir.")
        return
    if a.subgroup_id is None:
        raise _invalid("Bölünýän sapak: her kiçi topar üçin subgroup_id görkeziň.")
    sub = db.get(m.Subgroup, a.subgroup_id)
    if sub is None or sub.group_id != item.group_id:
        raise _invalid("Kiçi topar bu sapagyň toparyna degişli däl.")


router.include_router(build_crud_router(
    model=m.Subject, create_schema=s.SubjectCreate, update_schema=s.SubjectUpdate,
    read_schema=s.SubjectRead, prefix="/subjects", tag="Dersler", filters=("department_id",),
))
router.include_router(build_crud_router(
    model=m.Stream, create_schema=s.StreamCreate, update_schema=s.StreamUpdate,
    read_schema=s.StreamRead, prefix="/streams", tag="Potoklar", apply=apply_stream,
))
router.include_router(build_crud_router(
    model=m.CurriculumItem, create_schema=s.CurriculumItemCreate, update_schema=s.CurriculumItemUpdate,
    read_schema=s.CurriculumItemRead, prefix="/curriculum", tag="Okuw meýilnamasy",
    filters=("group_id", "stream_id", "subject_id"), search_field=None, order_by=("id",),
    validate=validate_curriculum_item,
))
router.include_router(build_crud_router(
    model=m.TeachingAssignment, create_schema=s.TeachingAssignmentCreate,
    update_schema=s.TeachingAssignmentUpdate, read_schema=s.TeachingAssignmentRead,
    prefix="/assignments", tag="Mugallym bellemek", filters=("curriculum_item_id", "teacher_id"),
    search_field=None, order_by=("id",), validate=validate_assignment,
))
