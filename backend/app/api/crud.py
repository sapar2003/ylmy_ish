"""Ähli esasy sanawlar (fakultet, kafedra, ...) üçin umumy CRUD router.

Täze sanaw goşmak = model + schema + `build_crud_router(...)` bilen bir setir.
"""
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
    return HTTPException(status.HTTP_409_CONFLICT, "Şeýle ýazga eýýäm bar (ady ýa-da kody gaýtalanýar).")


def build_crud_router(
    *,
    model: type[Base],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    read_schema: type[BaseModel],
    prefix: str,
    tag: str,
    filters: tuple[str, ...] = (),
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    def get_or_404(db: Session, item_id: int) -> Any:
        obj = db.get(model, item_id)
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{tag}: id={item_id} tapylmady.")
        return obj

    def commit(db: Session, deleting: bool = False) -> None:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise _integrity_error(exc, deleting) from exc

    # Süzgüçler (meselem ?faculty_id=3) query model hökmünde yglan edilýär, OpenAPI-de görünýär.
    filter_model = create_model(
        f"{model.__name__}Filters",
        q=(str | None, Field(None, description="Ady boýunça gözleg")),
        limit=(int, Field(50, ge=1, le=500)),
        offset=(int, Field(0, ge=0)),
        **{f: (int | None, None) for f in filters},
    )

    @router.get("", response_model=Page[read_schema])
    def list_items(db: DbSession, params: Annotated[filter_model, Query()]):  # type: ignore[valid-type]
        stmt = select(model)
        if params.q:
            stmt = stmt.where(model.name.ilike(f"%{params.q}%"))
        for field in filters:
            value = getattr(params, field)
            if value is not None:
                stmt = stmt.where(getattr(model, field) == value)
        total = db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = db.scalars(stmt.order_by(model.name).limit(params.limit).offset(params.offset)).all()
        return Page(
            items=[read_schema.model_validate(r) for r in rows],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    @router.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED)
    def create_item(payload: create_schema, db: DbSession):  # type: ignore[valid-type]
        obj = model(**payload.model_dump())
        db.add(obj)
        commit(db)
        db.refresh(obj)
        return obj

    @router.get("/{item_id}", response_model=read_schema)
    def get_item(item_id: int, db: DbSession):
        return get_or_404(db, item_id)

    @router.patch("/{item_id}", response_model=read_schema)
    def update_item(item_id: int, payload: update_schema, db: DbSession):  # type: ignore[valid-type]
        obj = get_or_404(db, item_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(obj, key, value)
        commit(db)
        db.refresh(obj)
        return obj

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(item_id: int, db: DbSession):
        db.delete(get_or_404(db, item_id))
        commit(db, deleting=True)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
