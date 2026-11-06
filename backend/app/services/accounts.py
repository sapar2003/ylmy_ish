"""Hasaplar: mugallym üçin login ýasamak we admin döretmek.

Admin döretmek (ýa-da parolyny täzelemek):  python -m app.services.accounts admin [login]
"""
import re
import secrets
import sys
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.core.security import hash_password, new_password, verify_password
from app.services import sms

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


# --- telefon nomeri bilen giriş (mugallym we talyp app-y) ---
CODE_MINUTES = 5
RESEND_SECONDS = 60
MAX_ATTEMPTS = 5
MAX_PER_HOUR = 5


def normalize_phone(raw: str | None) -> str | None:
    """"65 123456", "+993 65 12-34-56" -> "+99365123456"; nädogry bolsa None."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 8:
        return "+993" + digits
    if len(digits) == 11 and digits.startswith("993"):
        return "+" + digits
    return None


def clean_phone(db: Session, obj: m.Teacher | m.Student) -> None:
    """Mugallymyň ýa-da talybyň nomerini bir görnüşe getirýär; bir nomer iki adamda bolup bilmez."""
    if not obj.phone or not obj.phone.strip():
        obj.phone = None
        return
    phone = normalize_phone(obj.phone)
    if phone is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Telefon nomeri nädogry. Meselem: +993 65 123456")
    obj.phone = phone
    for model in (m.Teacher, m.Student):
        other = db.scalar(select(model).where(model.phone == phone))
        if other is not None and other is not obj:
            raise HTTPException(status.HTTP_409_CONFLICT, "Bu telefon nomeri başga adamda bellenipdir.")


def user_by_phone(db: Session, phone: str) -> m.User | None:
    """Nomeri admin panelinde bellenen mugallymyň/talybyň hasaby; ilkinji gezekde parolsyz döredilýär."""
    teacher = db.scalar(select(m.Teacher).where(m.Teacher.phone == phone))
    student = None if teacher else db.scalar(select(m.Student).where(m.Student.phone == phone, m.Student.active.is_(True)))
    if teacher is None and student is None:
        return None
    if teacher:
        user = db.scalar(select(m.User).where(m.User.teacher_id == teacher.id))
    else:
        user = db.scalar(select(m.User).where(m.User.student_id == student.id))
    if user is None:
        taken = set(db.scalars(select(m.User.username)))
        name = username_for(teacher, taken) if teacher else f"talyp{student.id}"
        user = m.User(username=name, password_hash="", role=m.Role.teacher if teacher else m.Role.student,
                      teacher_id=teacher.id if teacher else None, student_id=student.id if student else None,
                      must_change_password=False, active=True)
        db.add(user)
        db.commit()
    return user if user.active else None


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def send_login_code(db: Session, phone: str) -> None:
    """Hasaby bar nomere kod iberýär. Çäkler: minutda 1, sagatda 5 (SMS çykdajysy we hüjüm üçin)."""
    if user_by_phone(db, phone) is None:
        return
    now = _now()
    row = db.scalar(select(m.LoginCode).where(m.LoginCode.phone == phone))
    if row is not None:
        if (now - row.last_sent_at).total_seconds() < RESEND_SECONDS:
            return
        if now - row.window_start >= timedelta(hours=1):
            row.window_start, row.sent_in_window = now, 0
        if row.sent_in_window >= MAX_PER_HOUR:
            return
    else:
        row = m.LoginCode(phone=phone, window_start=now, sent_in_window=0)
        db.add(row)
    code = f"{secrets.randbelow(1_000_000):06d}"
    row.code_hash, row.attempts = hash_password(code), 0
    row.expires_at, row.last_sent_at = now + timedelta(minutes=CODE_MINUTES), now
    row.sent_in_window += 1
    db.commit()
    sms.send_sms(phone, f"Raspisaniye giris kody: {code}")


def check_login_code(db: Session, phone: str, code: str) -> m.User | None:
    """Dogry kod bir gezek işleýär; 5 ýalňyşdan ýa-da 5 minutdan soň güýji ýok."""
    row = db.scalar(select(m.LoginCode).where(m.LoginCode.phone == phone))
    if row is None or row.expires_at < _now() or row.attempts >= MAX_ATTEMPTS:
        return None
    if not verify_password(code.strip(), row.code_hash):
        row.attempts += 1
        db.commit()
        return None
    # Kod ulanyldy: täze kod çäkleri saklanýar, bu kod bolsa indi işlemeýär.
    row.expires_at = _now()
    row.attempts = MAX_ATTEMPTS
    db.commit()
    return user_by_phone(db, phone)


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
