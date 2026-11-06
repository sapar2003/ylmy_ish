"""Giriş, hasaplar (admin) we mugallymyň öz raspisaniýesi (mobil app üçin)."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app import models as m
from app.api.auth import CurrentUser, TeacherUser, require_admin
from app.api.crud import DbSession, get_or_404
from app.api.v1.exams import list_entries as exam_entries
from app.api.v1.timetables import list_entries as timetable_entries
from app.api.v1.timetables import week_of
from app.api.v1.topics import week_topics
from app.core.security import create_token, hash_password, verify_password
from app.schemas import user as s
from app.schemas.timetable import Ref
from app.services.accounts import (
    check_login_code,
    create_dean_account,
    create_teacher_accounts,
    normalize_phone,
    reset_password,
    send_login_code,
    user_by_phone,
)

router = APIRouter()


def _ref(o) -> Ref | None:
    return Ref(id=o.id, name=o.name) if o else None


def _me(db, user: m.User) -> s.MeRead:
    teacher = db.get(m.Teacher, user.teacher_id) if user.teacher_id else None
    faculty = db.get(m.Faculty, user.faculty_id) if user.faculty_id else None
    return s.MeRead(id=user.id, username=user.username, role=user.role, must_change_password=user.must_change_password,
                    teacher=_ref(teacher), faculty=_ref(faculty), student=_student_info(db, user),
                    teacher_info=_teacher_info(db, teacher),
                    has_password=bool(user.password_hash))


def _teacher_info(db, teacher: m.Teacher | None) -> s.TeacherInfo | None:
    if teacher is None:
        return None
    dep = db.get(m.Department, teacher.department_id)
    fac = db.get(m.Faculty, dep.faculty_id) if dep else None
    return s.TeacherInfo(position=teacher.position, department=dep.name if dep else None,
                         faculty=(fac.short_name or fac.name) if fac else None, phone=teacher.phone)


def _student_info(db, user: m.User) -> s.StudentInfo | None:
    st = db.get(m.Student, user.student_id) if user.student_id else None
    if st is None:
        return None
    group = db.get(m.Group, st.group_id)
    sub = db.get(m.Subgroup, st.subgroup_id) if st.subgroup_id else None
    spec = db.get(m.Specialty, group.specialty_id)
    dep = db.get(m.Department, spec.department_id)
    fac = db.get(m.Faculty, dep.faculty_id)
    return s.StudentInfo(id=st.id, name=st.full_name, group_id=group.id, group=group.name,
                         subgroup_id=sub.id if sub else None, subgroup=sub.name if sub else None,
                         faculty=fac.short_name or fac.name, course=group.course, phone=st.phone)


# --- giriş ---
auth = APIRouter(prefix="/auth", tags=["Giriş"])


@auth.post("/login", response_model=s.LoginOut)
def login(payload: s.LoginIn, db: DbSession):
    user = db.scalar(select(m.User).where(m.User.username == payload.username.strip().lower()))
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login ýa-da parol nädogry.")
    return s.LoginOut(**_me(db, user).model_dump(), token=create_token(user.id))


def _phone(raw: str) -> str:
    phone = normalize_phone(raw)
    if phone is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Telefon nomeri nädogry. Meselem: +993 65 123456")
    return phone


@auth.post("/phone-login", response_model=s.LoginOut)
def phone_login(payload: s.PhoneLoginIn, db: DbSession):
    """Mugallym we talyp: telefon nomeri we parol."""
    user = user_by_phone(db, _phone(payload.phone))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Telefon nomeri ýa-da parol nädogry.")
    return s.LoginOut(**_me(db, user).model_dump(), token=create_token(user.id))


@auth.post("/otp/request")
def otp_request(payload: s.OtpRequestIn, db: DbSession):
    """Telefona giriş kody. Jogap nomeriň bazada bardygyny aýtmaýar."""
    send_login_code(db, _phone(payload.phone))
    return {"ok": True}


@auth.post("/otp/verify", response_model=s.LoginOut)
def otp_verify(payload: s.OtpVerifyIn, db: DbSession):
    user = check_login_code(db, _phone(payload.phone), payload.code)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kod nädogry ýa-da möhleti geçdi.")
    return s.LoginOut(**_me(db, user).model_dump(), token=create_token(user.id))


@auth.post("/set-password", response_model=s.MeRead)
def set_password(payload: s.SetPasswordIn, user: CurrentUser, db: DbSession):
    """Paroly ýok hasaba (kod bilen giren) ilkinji paroly goýmak."""
    if user.password_hash:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Paroluňyz bar: "Paroly çalyş" ulanyň.')
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return _me(db, user)


@auth.get("/me", response_model=s.MeRead)
def me(user: CurrentUser, db: DbSession):
    return _me(db, user)


@auth.post("/change-password", response_model=s.MeRead)
def change_password(payload: s.ChangePasswordIn, user: CurrentUser, db: DbSession):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Häzirki parol nädogry.")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    db.commit()
    return _me(db, user)


router.include_router(auth)

# --- hasaplar (admin) ---
users = APIRouter(prefix="/users", tags=["Hasaplar"], dependencies=[Depends(require_admin)])


def _user_read(user: m.User, teachers: dict[int, m.Teacher], faculties: dict[int, m.Faculty]) -> s.UserRead:
    return s.UserRead(id=user.id, username=user.username, role=user.role, active=user.active,
                      must_change_password=user.must_change_password,
                      teacher=_ref(teachers.get(user.teacher_id)), faculty=_ref(faculties.get(user.faculty_id)))


@users.get("", response_model=list[s.UserRead])
def list_users(db: DbSession):
    teachers = {t.id: t for t in db.scalars(select(m.Teacher))}
    faculties = {f.id: f for f in db.scalars(select(m.Faculty))}
    return [_user_read(u, teachers, faculties)
            for u in db.scalars(select(m.User).order_by(m.User.role, m.User.username))]


@users.post("/deans", response_model=s.IssuedPassword, status_code=status.HTTP_201_CREATED)
def create_dean_user(payload: s.DeanAccountIn, db: DbSession):
    """Fakultetiň dekan hasaby: dekan diňe öz fakultetiniň maglumatlaryny görýär we girizýär.
    Hasap bar bolsa täze wagtlaýyn parol berilýär."""
    faculty = get_or_404(db, m.Faculty, payload.faculty_id, "Fakultet")
    user, password = create_dean_account(db, faculty)
    return s.IssuedPassword(user_id=user.id, username=user.username, password=password, teacher=None,
                            faculty=_ref(faculty))


@users.post("/teachers", response_model=list[s.IssuedPassword], status_code=status.HTTP_201_CREATED)
def create_teacher_users(payload: s.TeacherAccountsIn, db: DbSession):
    """Mugallymlara hasap açýar. Wagtlaýyn parollar diňe şu jogapda görkezilýär — çap edip paýlaň."""
    teachers = {t.id: t for t in db.scalars(select(m.Teacher))}
    return [
        s.IssuedPassword(user_id=u.id, username=u.username, password=pw,
                         teacher=Ref(id=u.teacher_id, name=teachers[u.teacher_id].name))
        for u, pw in create_teacher_accounts(db, payload.teacher_ids)
    ]


@users.post("/{user_id}/reset-password", response_model=s.IssuedPassword)
def reset_user_password(user_id: int, db: DbSession):
    user = get_or_404(db, m.User, user_id, "Ulanyjy")
    t = db.get(m.Teacher, user.teacher_id) if user.teacher_id else None
    f = db.get(m.Faculty, user.faculty_id) if user.faculty_id else None
    return s.IssuedPassword(user_id=user.id, username=user.username, password=reset_password(db, user),
                            teacher=_ref(t), faculty=_ref(f))


@users.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DbSession, admin: m.User = Depends(require_admin)):
    user = get_or_404(db, m.User, user_id, "Ulanyjy")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Öz hasabyňyzy aýryp bilmersiňiz.")
    db.delete(user)
    db.commit()


router.include_router(users)

# --- çap etmek (admin): mugallymlar diňe çap edilen raspisaniýäni görýär ---
publish = APIRouter(tags=["Çap etmek"], dependencies=[Depends(require_admin)])


@publish.post("/timetables/{timetable_id}/publish")
def publish_timetable(timetable_id: int, payload: s.PublishIn, db: DbSession):
    tt = get_or_404(db, m.Timetable, timetable_id, "Raspisaniýe")
    if payload.published and tt.status != m.TimetableStatus.done:
        raise HTTPException(status.HTTP_409_CONFLICT, "Diňe taýýar raspisaniýäni çap edip bolýar.")
    if payload.published:
        for other in db.scalars(select(m.Timetable).where(m.Timetable.published.is_(True))):
            other.published = False
    tt.published = payload.published
    db.commit()
    return {"id": tt.id, "published": tt.published}


@publish.post("/exam-schedules/{schedule_id}/publish")
def publish_exam_schedule(schedule_id: int, payload: s.PublishIn, db: DbSession):
    sch = get_or_404(db, m.ExamSchedule, schedule_id, "Synag raspisaniýesi")
    if payload.published and sch.status != m.TimetableStatus.done:
        raise HTTPException(status.HTTP_409_CONFLICT, "Diňe taýýar synag raspisaniýesini çap edip bolýar.")
    if payload.published:  # şol möwsümiň beýleki wersiýalary ýapylýar
        for other in db.scalars(select(m.ExamSchedule).where(m.ExamSchedule.session_id == sch.session_id,
                                                             m.ExamSchedule.published.is_(True))):
            other.published = False
    sch.published = payload.published
    db.commit()
    return {"id": sch.id, "published": sch.published}


router.include_router(publish)

# --- mugallymyň öz raspisaniýesi (mobil app) ---
me_router = APIRouter(prefix="/me", tags=["Meniň raspisaniýäm"])


@me_router.get("/timetable", response_model=s.MyWeekRead)
def my_timetable(user: TeacherUser, db: DbSession, on: date | None = None):
    """Çap edilen raspisaniýeden diňe şu mugallymyň sapaklary; `on` senäniň hepdesi (sanawjy/maýdalawjy)."""
    tt = db.scalar(select(m.Timetable).where(m.Timetable.published.is_(True)))
    if tt is None:
        return s.MyWeekRead(timetable=None)
    on = on or date.today()
    week = week_of(tt, on)
    entries = timetable_entries(tt.id, db, group_id=None, teacher_id=user.teacher_id, room_id=None, week=week, on=None)
    start = on - timedelta(days=on.weekday())
    return s.MyWeekRead(timetable=Ref(id=tt.id, name=tt.name), weeks=tt.weeks, week=week, week_start=start,
                        entries=entries, topics=week_topics(db, {e.assignment_id for e in entries}, start))


@me_router.get("/exams", response_model=list[s.MyExamRead])
def my_exams(user: TeacherUser, db: DbSession):
    """Çap edilen synag raspisaniýelerinden şu mugallymyň uly ýa-da kiçi mugallym bolan synaglary."""
    out = []
    for sch in db.scalars(select(m.ExamSchedule).where(m.ExamSchedule.published.is_(True))):
        session = db.get(m.ExamSession, sch.session_id)
        for e in exam_entries(sch.id, db, group_id=None, teacher_id=user.teacher_id, room_id=None):
            examiner = e.examiner.id == user.teacher_id
            out.append(s.MyExamRead(
                schedule=Ref(id=sch.id, name=sch.name), session=Ref(id=session.id, name=session.name),
                kind=session.kind.value, day=e.day, starts_at=e.starts_at.strftime("%H:%M"),
                ends_at=e.ends_at.strftime("%H:%M"), subject=e.subject, role="examiner" if examiner else "assistant",
                groups=e.groups, room=e.room, partner=e.assistant if examiner else e.examiner,
            ))
    return sorted(out, key=lambda x: (x.day, x.starts_at))


router.include_router(me_router)
