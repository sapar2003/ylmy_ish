from dataclasses import dataclass, field


@dataclass(frozen=True)
class Slot:
    id: int
    weekday: int
    number: int
    shift_id: int


@dataclass(frozen=True)
class Room:
    id: int
    capacity: int
    room_type_id: int


@dataclass(frozen=True)
class Teacher:
    id: int
    name: str
    max_per_day: int | None = None
    max_per_week: int | None = None
    unavailable: frozenset[int] = frozenset()  # slot id
    preferred: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Lesson:
    """Bir mugallymyň bir topar/potok/kiçi topar bilen hepdede `per_week` gezek geçýän sapagy."""

    key: str  # durnukly at, netijäni yzyna baglamak üçin
    curriculum_item_id: int
    assignment_id: int
    teacher_id: int
    group_ids: tuple[int, ...]  # potokda birnäçe topar
    subgroup_id: int | None  # bölünýän sapakda kiçi topar
    per_week: int
    size: int  # talyp sany
    room_type_id: int | None
    allowed_slots: frozenset[int]  # toparyň smenasy boýunça
    label: str = ""  # adam üçin: "PO-101 · Matematika (amaly) · A. Annaýew"


@dataclass
class SolverInput:
    slots: list[Slot]
    rooms: list[Room]
    teachers: dict[int, Teacher]
    lessons: list[Lesson]
    subgroups_of: dict[int, list[int]] = field(default_factory=dict)  # group_id -> [subgroup_id]
    time_limit_seconds: float = 60
    workers: int = 8


@dataclass
class Placement:
    lesson_key: str
    slot_id: int
    room_id: int | None


@dataclass
class SolverResult:
    ok: bool
    status: str
    placements: list[Placement] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    objective: float | None = None
    seconds: float = 0
