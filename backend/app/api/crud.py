"""Ähli esasy sanawlar (fakultet, kafedra, ...) üçin umumy CRUD router.

Täze sanaw goşmak = model + schema + `build_crud_router(...)` bilen bir setir.
"""
from collections.abc import Callable
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
) -> APIRouter:
    """`router` berilse, CRUD şol routere goşulýar (goşmaça endpointler bilen birlikde).

    `apply(db, obj, data)` maglumaty obýekte geçirýär (meselem, id sanawyny baglanyşyga öwürmek);
    `validate(db, obj)` ýatda saklamazdan öň barlaýar we ýalňyşlykda HTTPException atýar.
    """

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

    def get_item_or_404(db: Session, item_id: int) -> Any:
        return get_or_404(db, model, item_id, tag)

    # Süzgüçler (meselem ?faculty_id=3) query model hökmünde yglan edilýär, OpenAPI-de görünýär.
    filter_model = create_model(
        f"{model.__name__}Filters",
        **({"q": (str | None, Field(None, description="Ady boýunça gözleg"))} if search_field else {}),
        limit=(int, Field(50, ge=1, le=500)),
        offset=(int, Field(0, ge=0)),
        **{f: (int | None, None) for f in filters},
    )

    @router.get("", response_model=Page[read_schema])
    def list_items(db: DbSession, params: Annotated[filter_model, Query()]):  # type: ignore[valid-type]
        stmt = select(model)
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
    def create_item(payload: create_schema, db: DbSession):  # type: ignore[valid-type]
        obj = model()
        apply_data(db, obj, payload.model_dump())
        return save(db, obj)

    @router.get("/{item_id}", response_model=read_schema)
    def get_item(item_id: int, db: DbSession):
        return get_item_or_404(db, item_id)

    @router.patch("/{item_id}", response_model=read_schema)
    def update_item(item_id: int, payload: update_schema, db: DbSession):  # type: ignore[valid-type]
        obj = get_item_or_404(db, item_id)
        apply_data(db, obj, payload.model_dump(exclude_unset=True))
        return save(db, obj)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(item_id: int, db: DbSession):
        db.delete(get_item_or_404(db, item_id))
        commit(db, deleting=True)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
