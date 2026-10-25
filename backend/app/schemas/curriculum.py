from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import LessonType
from app.schemas.structure import ReadBase


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=30)
    department_id: int


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=30)
    department_id: int | None = None


class SubjectRead(ReadBase, SubjectCreate):
    pass


class StreamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    group_ids: list[int] = Field(min_length=2, description="Potokdaky toparlar (iň az 2)")


class StreamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    group_ids: list[int] | None = Field(default=None, min_length=2)


class StreamRead(ReadBase, StreamCreate):
    pass


def _none_is_zero(v):
    return 0 if v is None else v


class CurriculumItemCreate(BaseModel):
    subject_id: int
    lesson_type: LessonType
    lessons_per_week: int = Field(ge=0, le=20, description="Her hepde geçýän sapak sany")
    biweekly: int = Field(default=0, ge=0, le=20, description="Iki hepdede bir geçýän sapak sany")
    group_id: int | None = None
    stream_id: int | None = None
    split: bool = False
    room_type_id: int | None = None

    _biweekly = field_validator("biweekly", mode="before")(_none_is_zero)

    @model_validator(mode="after")
    def _some_lessons(self):
        if self.lessons_per_week + self.biweekly == 0:
            raise ValueError("Her hepde ýa-da iki hepdede bir — iň az bir sapak bolmaly")
        return self


class CurriculumItemUpdate(BaseModel):
    subject_id: int | None = None
    lesson_type: LessonType | None = None
    lessons_per_week: int | None = Field(default=None, ge=0, le=20)
    biweekly: int | None = Field(default=None, ge=0, le=20)

    _biweekly = field_validator("biweekly", mode="before")(_none_is_zero)  # formadaky boş meýdan = 0
    group_id: int | None = None
    stream_id: int | None = None
    split: bool | None = None
    room_type_id: int | None = None


class CurriculumItemRead(ReadBase, CurriculumItemCreate):
    pass


class TeachingAssignmentCreate(BaseModel):
    curriculum_item_id: int
    teacher_id: int
    subgroup_id: int | None = Field(default=None, description="Diňe bölünýän sapak üçin")


class TeachingAssignmentUpdate(BaseModel):
    teacher_id: int | None = None
    subgroup_id: int | None = None


class TeachingAssignmentRead(ReadBase, TeachingAssignmentCreate):
    pass
