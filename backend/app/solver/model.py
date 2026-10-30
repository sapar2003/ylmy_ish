from dataclasses import dataclass, field


@dataclass(frozen=True)
class Slot:
    id: int
    weekday: int
    number: int
    shift_id: int
    start: int = 0  # başlanýan wagty, minut (08:30 -> 510): dürli smenalaryň slotlaryny deňeşdirmek üçin


@dataclass(frozen=True)
class Room:
    id: int
    capacity: int
    room_type_id: int
    faculty_id: int | None = None  # None: umumy otag


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
    faculty_ids: frozenset[int] = frozenset()  # toparlaryň fakultetleri: diňe olaryň we umumy otaglar
    # Iki hepdede bir geçýän sapaklaryň sany (1-nji ýa-da 2-nji hepdede). Bir hepdelik raspisaniýede
    # olar her hepde geçýän sapak hasaplanýar.
    biweekly: int = 0


@dataclass
class SolverInput:
    slots: list[Slot]
    rooms: list[Room]
    teachers: dict[int, Teacher]
    lessons: list[Lesson]
    subgroups_of: dict[int, list[int]] = field(default_factory=dict)  # group_id -> [subgroup_id]
    time_limit_seconds: float = 60
    workers: int = 8
    weeks: int = 1  # 1: her hepde birmeňzeş; 2: 1-nji we 2-nji hepde (sanawjy/maýdalawjy)


@dataclass
class Placement:
    lesson_key: str
    slot_id: int
    room_id: int | None
    week: int | None = None  # None: her hepde; 1 ýa-da 2: diňe şol hepde


@dataclass
class SolverResult:
    ok: bool
    status: str
    placements: list[Placement] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    objective: float | None = None
    seconds: float = 0
