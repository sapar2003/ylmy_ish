from datetime import date

from pydantic import BaseModel, Field

from app.models import Role
from app.schemas.timetable import EntryRead, Ref
from app.schemas.topic import TopicRead


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class StudentInfo(BaseModel):
    """Talybyň app-da görýän raspisaniýesi şu topar boýunça."""
    id: int
    name: str
    group_id: int
    group: str
    subgroup_id: int | None = None
    subgroup: str | None = None
    faculty: str | None = None
    course: int | None = None
    phone: str | None = None


class TeacherInfo(BaseModel):
    """Mugallymyň app-daky profili."""
    position: str | None = None
    department: str | None = None
    faculty: str | None = None
    phone: str | None = None


class MeRead(BaseModel):
    id: int
    username: str
    role: Role
    teacher: Ref | None
    faculty: Ref | None = None  # dekan üçin
    student: StudentInfo | None = None
    teacher_info: TeacherInfo | None = None
    has_password: bool = True
    must_change_password: bool


class PhoneLoginIn(BaseModel):
    phone: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=1, max_length=200)


class OtpRequestIn(BaseModel):
    phone: str = Field(min_length=1, max_length=30)


class OtpVerifyIn(BaseModel):
    phone: str = Field(min_length=1, max_length=30)
    code: str = Field(min_length=1, max_length=10)


class SetPasswordIn(BaseModel):
    new_password: str = Field(min_length=6, max_length=200, description="Iň az 6 harp")


class LoginOut(MeRead):
    token: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=200, description="Iň az 6 harp")


class UserRead(BaseModel):
    id: int
    username: str
    role: Role
    teacher: Ref | None
    faculty: Ref | None = None
    must_change_password: bool
    active: bool


class TeacherAccountsIn(BaseModel):
    teacher_ids: list[int] | None = Field(default=None, description="Berilmese: hasaby ýok ähli mugallymlar")


class IssuedPassword(BaseModel):
    """Wagtlaýyn parol diňe şu jogapda görkezilýär (bazada diňe heşi saklanýar)."""
    user_id: int
    username: str
    password: str
    teacher: Ref | None
    faculty: Ref | None = None


class DeanAccountIn(BaseModel):
    faculty_id: int


class PublishIn(BaseModel):
    published: bool = True


class MyWeekRead(BaseModel):
    timetable: Ref | None  # çap edilen raspisaniýe ýok bolsa None
    weeks: int = 1
    week: int | None = None  # 1 sanawjy, 2 maýdalawjy (iki hepdelik raspisaniýede)
    week_start: date | None = None
    entries: list[EntryRead] = []
    topics: list[TopicRead] = []  # şu hepdäniň sapaklarynyň temalary we faýllary


class MyExamRead(BaseModel):
    schedule: Ref
    session: Ref
    kind: str
    day: date
    starts_at: str
    ends_at: str
    subject: Ref
    role: str  # "examiner" (uly) ýa-da "assistant" (kiçi)
    groups: list[Ref]
    room: Ref | None
    partner: Ref | None  # beýleki mugallym
