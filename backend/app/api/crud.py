"""Ähli esasy sanawlar (fakultet, kafedra, ...) üçin umumy CRUD router.

Täze sanaw goşmak = model + schema + `build_crud_router(...)` bilen bir setir.
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, create_model
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


def _integrity_error(exc: IntegrityError, deleting: bool) -> HTTPException:
    msg = str(exc.orig).lower()
    if "foreign key" in msg:
        if deleting:
            return HTTPException(
                status.HTTP_409_CONFLICT,
                "Bu ýazga başga ýazgylar bagly (meselem, fakultetde kafedra bar). Ilki olary aýyryň.",
            )
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Görkezilen baglanyşyk (…_id) tapylmady.")
    if "check constraint" in msg or "violates check" in msg:
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Maglumatlar biri-birine laýyk däl.")
    return HTTPException(status.HTTP_409_CONFLICT, "Şeýle ýazga eýýäm bar (ady ýa-da kody gaýtalanýar).")


def commit_or_raise(db: Session, deleting: bool = False) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _integrity_error(exc, deleting) from exc


def get_or_404(db: Session, model: type[Base], item_id: int, label: str) -> Any:
    obj = db.get(model, item_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label}: id={item_id} tapylmady.")
    return obj


@dataclass(frozen=True)
class Scope:
    """Dekan üçin çäkler: `owner(db, obj)` — ýazgynyň fakulteti (None: umumy, diňe admin üýtgedýär);
    `visible(faculty_id)` — dekanyň görýän ýazgylarynyň SQL şerti (None: hemmesi görünýär)."""

    owner: Callable[[Session, Any], int | None] = lambda db, obj: None
    visible: Callable[[int], Any] | None = None


GLOBAL = Scope()  # umumy sanawlar (smenalar, binalar, ...): dekan diňe görýär

NOT_YOURS = "Bu başga fakultetiň ýa-da umumy maglumat: diňe görüp bilersiňiz."


def check_owner(scope: Scope, db: Session, obj: Any, faculty_id: int | None) -> None:
    """Dekan diňe öz fakultetiniň ýazgysyny üýtgedip bilýär (admin üçin `faculty_id` None)."""
    if faculty_id is None:
        return
    with db.no_autoflush:
        owner = scope.owner(db, obj)
    if owner != faculty_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NOT_YOURS)


def build_crud_router(
    *,
    model: type[Base],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    read_schema: type[BaseModel],
    prefix: str,
    tag: str,
    filters: tuple[str, ...] = (),
    search_field: str | None = "name",
    order_by: tuple[str, ...] = ("name",),
    router: APIRouter | None = None,
    apply: Callable[[Session, Any, dict[str, Any]], None] | None = None,
    validate: Callable[[Session, Any], None] | None = None,
    scope: Scope = GLOBAL,
) -> APIRouter:
    """`router` berilse, CRUD şol routere goşulýar (goşmaça endpointler bilen birlikde).

    `apply(db, obj, data)` maglumaty obýekte geçirýär (meselem, id sanawyny baglanyşyga öwürmek);
    `validate(db, obj)` ýatda saklamazdan öň barlaýar we ýalňyşlykda HTTPException atýar.
    `scope` dekanyň näme görýändigini we näme üýtgedip bilýändigini kesgitleýär.
    """
    from app.api.auth import FacultyScope  # auth bu modula bagly: aýlawly importdan gaça durmak

    def apply_data(db: Session, obj: Any, data: dict[str, Any]) -> None:
        if apply:
            apply(db, obj, data)
        else:
            for key, value in data.items():
                setattr(obj, key, value)

    def save(db: Session, obj: Any) -> Any:
        if validate:
            with db.no_autoflush:
                validate(db, obj)
        db.add(obj)
        commit(db)
        db.refresh(obj)
        return obj
    router = router or APIRouter(prefix=prefix, tags=[tag])
    commit = commit_or_raise

    def get_item_or_404(db: Session, item_id: int, faculty_id: int | None = None) -> Any:
        obj = get_or_404(db, model, item_id, tag)
        if faculty_id is not None and scope.visible is not None and db.scalar(
                select(model.id).where(model.id == item_id, scope.visible(faculty_id))) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{tag}: id={item_id} tapylmady.")
        return obj

    # Süzgüçler (meselem ?faculty_id=3) query model hökmünde yglan edilýär, OpenAPI-de görünýär.
    filter_model = create_model(
        f"{model.__name__}Filters",
        **({"q": (str | None, Field(None, description="Ady boýunça gözleg"))} if search_field else {}),
        limit=(int, Field(50, ge=1, le=500)),
        offset=(int, Field(0, ge=0)),
        **{f: (int | None, None) for f in filters},
    )

    @router.get("", response_model=Page[read_schema])
    def list_items(db: DbSession, params: Annotated[filter_model, Query()], fid: FacultyScope):  # type: ignore[valid-type]
        stmt = select(model)
        if fid is not None and scope.visible is not None:
            stmt = stmt.where(scope.visible(fid))
        if search_field and params.q:
            stmt = stmt.where(getattr(model, search_field).ilike(f"%{params.q}%"))
        for field in filters:
            value = getattr(params, field)
            if value is not None:
                stmt = stmt.where(getattr(model, field) == value)
        total = db.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.order_by(*(getattr(model, f) for f in order_by))
        rows = db.scalars(stmt.limit(params.limit).offset(params.offset)).all()
        return Page(
            items=[read_schema.model_validate(r) for r in rows],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    @router.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED)
    def create_item(payload: create_schema, db: DbSession, fid: FacultyScope):  # type: ignore[valid-type]
        obj = model()
        apply_data(db, obj, payload.model_dump())
        check_owner(scope, db, obj, fid)
        return save(db, obj)

    @router.get("/{item_id}", response_model=read_schema)
    def get_item(item_id: int, db: DbSession, fid: FacultyScope):
        return get_item_or_404(db, item_id, fid)

    @router.patch("/{item_id}", response_model=read_schema)
    def update_item(item_id: int, payload: update_schema, db: DbSession, fid: FacultyScope):  # type: ignore[valid-type]
        obj = get_item_or_404(db, item_id, fid)
        check_owner(scope, db, obj, fid)
        apply_data(db, obj, payload.model_dump(exclude_unset=True))
        check_owner(scope, db, obj, fid)  # başga fakultete geçirip bolmaýar
        return save(db, obj)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(item_id: int, db: DbSession, fid: FacultyScope):
        obj = get_item_or_404(db, item_id, fid)
        check_owner(scope, db, obj, fid)
        db.delete(obj)
        commit(db, deleting=True)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
