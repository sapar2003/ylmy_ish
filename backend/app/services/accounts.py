"""Hasaplar: mugallym üçin login ýasamak we admin döretmek.

Admin döretmek (ýa-da parolyny täzelemek):  python -m app.services.accounts admin [login]
"""
import re
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.core.security import hash_password, new_password

_LATIN = str.maketrans({"ä": "a", "ç": "ch", "ň": "n", "ö": "o", "ş": "sh", "ü": "u", "ý": "y", "ž": "zh"})


def username_for(teacher: m.Teacher, taken: set[str]) -> str:
    """"Arrykowa Güljemal ..." -> "arrykowa.g", "Hudaýgulyýewa G." -> "hudaygulyyewa.g"; gaýtalansa san goşulýar."""
    parts = [re.sub(r"[^a-z0-9]", "", w.lower().translate(_LATIN)) for w in teacher.name.split()]
    parts = [w for w in parts if w]
    base = parts[0] if parts else f"mugallym{teacher.id}"
    if len(parts) > 1:
        base += "." + parts[1][0]
    name, n = base, 2
    while name in taken:
        name, n = f"{base}{n}", n + 1
    taken.add(name)
    return name


def create_teacher_accounts(db: Session, teacher_ids: list[int] | None) -> list[tuple[m.User, str]]:
    """Hasaby ýok mugallymlara hasap açýar; (ulanyjy, wagtlaýyn parol) sanawyny gaýtarýar."""
    has_account = set(db.scalars(select(m.User.teacher_id).where(m.User.teacher_id.is_not(None))))
    taken = set(db.scalars(select(m.User.username)))
    stmt = select(m.Teacher).order_by(m.Teacher.name)
    if teacher_ids is not None:
        stmt = stmt.where(m.Teacher.id.in_(teacher_ids))
    issued = []
    for t in db.scalars(stmt):
        if t.id in has_account:
            continue
        password = new_password()
        user = m.User(username=username_for(t, taken), password_hash=hash_password(password), role=m.Role.teacher,
                      teacher_id=t.id, must_change_password=True, active=True)
        db.add(user)
        issued.append((user, password))
    db.commit()
    return issued


def create_dean_account(db: Session, faculty: m.Faculty) -> tuple[m.User, str]:
    """Fakultetiň dekan hasaby ("dekan.stkf"); bar bolsa täze wagtlaýyn parol berilýär."""
    user = db.scalar(select(m.User).where(m.User.role == m.Role.dean, m.User.faculty_id == faculty.id))
    if user is not None:
        return user, reset_password(db, user)
    label = faculty.short_name or faculty.code or f"f{faculty.id}"
    base = "dekan." + (re.sub(r"[^a-z0-9]", "", label.lower().translate(_LATIN)) or f"f{faculty.id}")
    taken = set(db.scalars(select(m.User.username)))
    name, n = base, 2
    while name in taken:
        name, n = f"{base}{n}", n + 1
    password = new_password()
    user = m.User(username=name, password_hash=hash_password(password), role=m.Role.dean, faculty_id=faculty.id,
                  must_change_password=True, active=True)
    db.add(user)
    db.commit()
    return user, password


def reset_password(db: Session, user: m.User) -> str:
    password = new_password()
    user.password_hash = hash_password(password)
    user.must_change_password = True
    db.commit()
    return password


def ensure_admin(db: Session, username: str = "admin") -> str:
    """Admin hasaby döredýär ýa-da parolyny täzeleýär; täze paroly gaýtarýar."""
    user = db.scalar(select(m.User).where(m.User.username == username))
    password = new_password(10)
    if user is None:
        user = m.User(username=username, role=m.Role.admin, teacher_id=None, active=True,
                      password_hash=hash_password(password), must_change_password=True)
        db.add(user)
    else:
        user.password_hash = hash_password(password)
        user.must_change_password = True
        user.role, user.active = m.Role.admin, True
    db.commit()
    return password


if __name__ == "__main__":
    from app.db.session import SessionLocal

    if len(sys.argv) < 2 or sys.argv[1] != "admin":
        sys.exit("Ulanylyşy: python -m app.services.accounts admin [login]")
    login = sys.argv[2] if len(sys.argv) > 2 else "admin"
    with SessionLocal() as session:
        print(f"login: {login}\nparol: {ensure_admin(session, login)}")
