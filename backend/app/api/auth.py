"""Kim girýär we näme edip bilýär: tokenden ulanyjy, admin, dekan we mugallym barlaglary."""
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import models as m
from app.api.crud import DbSession
from app.core.security import read_token

_bearer = HTTPBearer(auto_error=False)


def current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    token: Annotated[str | None, Query(include_in_schema=False)] = None,  # faýl ýüklemek üçin (?token=)
) -> m.User:
    raw = creds.credentials if creds else token
    uid = read_token(raw) if raw else None
    user = db.get(m.User, uid) if uid else None
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Giriň: login we parol gerek.",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[m.User, Depends(current_user)]


def require_admin(user: CurrentUser) -> m.User:
    if user.role != m.Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu diňe admin üçin.")
    return user


def require_staff(user: CurrentUser) -> m.User:
    """Admin ýa-da dekan: maglumatlary girizýänler (dekan diňe öz fakultetiniňkini, `faculty_scope`)."""
    if user.role == m.Role.dean and user.faculty_id is not None:
        return user
    if user.role != m.Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu diňe admin we dekan üçin.")
    return user


def faculty_scope(user: Annotated[m.User | None, Depends(require_staff)]) -> int | None:
    """Dekanyň fakulteti; admin üçin None (ähli fakultetler)."""
    return user.faculty_id if user is not None and user.role == m.Role.dean else None


FacultyScope = Annotated[int | None, Depends(faculty_scope)]


def require_teacher(user: CurrentUser) -> m.User:
    if user.role != m.Role.teacher or user.teacher_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu diňe mugallym hasaby üçin.")
    return user


TeacherUser = Annotated[m.User, Depends(require_teacher)]
