"""Solwerden öň aç-açan mümkin däl ýagdaýlary tapýar we düşnükli habar berýär."""
from collections import defaultdict

from app.solver.model import SolverInput


def room_allowed(room, item) -> bool:
    """Otagyň görnüşi we fakulteti laýykmy (sygymy hasaba alynmaýar).

    `item` sapak ýa-da synag bolup biler: `room_type_id` we `faculty_ids` meýdanlary bolmaly.
    """
    return (item.room_type_id is None or room.room_type_id == item.room_type_id) and (
        room.faculty_id is None or not item.faculty_ids or room.faculty_id in item.faculty_ids
    )


def eligible_rooms(rooms, item) -> list:
    return [r for r in rooms if r.capacity >= item.size and room_allowed(r, item)]


def teacher_slots(inp: SolverInput, lesson) -> set[int]:
    t = inp.teachers[lesson.teacher_id]
    return set(lesson.allowed_slots) - set(t.unavailable)


def precheck(inp: SolverInput) -> list[str]:
    issues: list[str] = []
    teacher_load: dict[int, int] = defaultdict(int)
    teacher_free: dict[int, set[int]] = defaultdict(set)
    group_load: dict[tuple[int, int | None], int] = defaultdict(int)
    group_slots: dict[int, set[int]] = defaultdict(set)

    for lesson in inp.lessons:
        free = teacher_slots(inp, lesson)
        if len(free) < lesson.per_week:
            issues.append(
                f"{lesson.label or lesson.key}: hepdede {lesson.per_week} sapak gerek, ýöne mugallymyň we toparyň "
                f"umumy boş slotlary diňe {len(free)}."
            )
        if not eligible_rooms(inp.rooms, lesson):
            issues.append(
                f"{lesson.label or lesson.key}: {lesson.size} talyp üçin laýyk otag (sygymy/görnüşi/fakulteti) ýok."
            )
        teacher_load[lesson.teacher_id] += lesson.per_week
        teacher_free[lesson.teacher_id] |= free
        for g in lesson.group_ids:
            group_load[(g, lesson.subgroup_id)] += lesson.per_week
            group_slots[g] |= set(lesson.allowed_slots)

    for tid, load in teacher_load.items():
        t = inp.teachers[tid]
        if t.max_per_week is not None and load > t.max_per_week:
            issues.append(f"Mugallym {t.name}: {load} sapak bellenipdir, hepdelik çäk {t.max_per_week}.")
        if load > len(teacher_free[tid]):
            issues.append(f"Mugallym {t.name}: {load} sapak bellenipdir, ýöne diňe {len(teacher_free[tid])} boş slot bar.")

    # Topar: umumy sapaklar + iň köp ýüklenen kiçi toparyň sapaklary slotlardan köp bolmaly däl.
    for g, slots in group_slots.items():
        common = group_load.get((g, None), 0)
        sub_max = max((group_load.get((g, sg), 0) for sg in inp.subgroups_of.get(g, [])), default=0)
        if common + sub_max > len(slots):
            issues.append(f"Topar id={g}: hepdede {common + sub_max} sapak, ýöne smenasynda {len(slots)} slot bar.")
    return issues
