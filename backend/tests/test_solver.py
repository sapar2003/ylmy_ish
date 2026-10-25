import dataclasses
from collections import Counter

from app.solver import Lesson, Room, Slot, SolverInput, Teacher, solve

SLOTS = [Slot(id=d * 10 + n, weekday=d, number=n, shift_id=1) for d in range(1, 6) for n in range(1, 4)]
ALL = frozenset(s.id for s in SLOTS)


def lesson(key, teacher, groups, per_week, size=20, subgroup=None, room_type=None, slots=ALL):
    return Lesson(
        key=key, curriculum_item_id=0, assignment_id=0, teacher_id=teacher, group_ids=tuple(groups),
        subgroup_id=subgroup, per_week=per_week, size=size, room_type_id=room_type, allowed_slots=slots,
    )


def base_input(lessons, rooms=None, teachers=None, subgroups_of=None):
    return SolverInput(
        slots=SLOTS,
        rooms=rooms or [Room(1, 30, 1), Room(2, 30, 1), Room(3, 100, 2)],
        teachers=teachers or {1: Teacher(1, "A"), 2: Teacher(2, "B"), 3: Teacher(3, "C")},
        lessons=lessons,
        subgroups_of=subgroups_of or {},
        time_limit_seconds=10,
        workers=4,
    )


def by_key(result):
    out = {}
    for p in result.placements:
        out.setdefault(p.lesson_key, []).append(p)
    return out


def test_shared_teacher_never_double_booked():
    # 1-nji mugallym iki dürli fakultetiň toparyna okadýar.
    lessons = [
        lesson("g1-math", 1, [1], 4),
        lesson("g2-math", 1, [2], 4),
        lesson("g1-phys", 2, [1], 3),
        lesson("g2-chem", 3, [2], 3),
    ]
    r = solve(base_input(lessons))
    assert r.ok, r.issues
    teacher1 = [p.slot_id for p in r.placements if p.lesson_key.endswith("math")]
    assert len(teacher1) == 8 and len(set(teacher1)) == 8
    for g in ("g1", "g2"):
        slots = [p.slot_id for p in r.placements if p.lesson_key.startswith(g)]
        assert len(slots) == len(set(slots))
    rooms_per_slot = Counter((p.slot_id, p.room_id) for p in r.placements)
    assert max(rooms_per_slot.values()) == 1


def test_split_lesson_subgroups_can_run_in_parallel_but_not_with_group():
    lessons = [
        lesson("lab-1", 1, [1], 2, size=12, subgroup=11),
        lesson("lab-2", 2, [1], 2, size=12, subgroup=12),
        lesson("lecture", 3, [1], 11),  # 15 slotyň 11-si umumy sapak
    ]
    r = solve(base_input(lessons, subgroups_of={1: [11, 12]}))
    assert r.ok, r.issues
    k = by_key(r)
    common = {p.slot_id for p in k["lecture"]}
    for sub in ("lab-1", "lab-2"):
        assert not common & {p.slot_id for p in k[sub]}
    # 15 - 11 = 4 boş slot, iki kiçi topara 2+2 = 4 sapak: diňe paralel goýlanda sygýar.
    assert len({p.slot_id for p in k["lab-1"]} | {p.slot_id for p in k["lab-2"]}) <= 4


def test_teacher_unavailability_and_shift_respected():
    morning = frozenset(s.id for s in SLOTS if s.number <= 2)
    t = {1: Teacher(1, "A", unavailable=frozenset({11, 12, 21, 22}))}
    r = solve(base_input([lesson("x", 1, [1], 5, slots=morning)], teachers=t))
    assert r.ok, r.issues
    used = {p.slot_id for p in r.placements}
    assert used <= morning and not used & {11, 12, 21, 22}


def test_room_type_and_capacity():
    lessons = [lesson("big", 1, [1, 2], 2, size=80), lesson("lab", 2, [3], 2, size=25, room_type=1)]
    r = solve(base_input(lessons))
    assert r.ok
    k = by_key(r)
    assert {p.room_id for p in k["big"]} == {3}
    assert {p.room_id for p in k["lab"]} <= {1, 2}


def test_rooms_of_other_faculty_not_used():
    # 1-nji otag 1-nji fakultetiňki, 2-nji umumy, 3-nji 2-nji fakultetiňki.
    rooms = [Room(1, 30, 1, faculty_id=1), Room(2, 30, 1), Room(3, 30, 1, faculty_id=2)]
    lessons = [
        Lesson(key=f"f2-{g}", curriculum_item_id=0, assignment_id=0, teacher_id=g, group_ids=(g,),
               subgroup_id=None, per_week=5, size=20, room_type_id=None, allowed_slots=ALL,
               faculty_ids=frozenset({2}))
        for g in (1, 2, 3)
    ]
    r = solve(base_input(lessons, rooms=rooms))
    assert r.ok, r.issues
    assert {p.room_id for p in r.placements} <= {2, 3}
    assert all(p.room_id is not None for p in r.placements)


def test_precheck_reports_impossible_load():
    t = {1: Teacher(1, "A", max_per_week=3)}
    r = solve(base_input([lesson("x", 1, [1], 5)], teachers=t))
    assert not r.ok and r.status == "precheck_failed"
    assert any("çäk 3" in i for i in r.issues)


def test_infeasible_reported():
    # Iki topar, bir mugallym, 15 slot, 16 sapak: precheck geçýär, solwer "ýok" diýýär.
    lessons = [lesson("a", 1, [1], 8), lesson("b", 1, [2], 8)]
    r = solve(base_input(lessons))
    assert not r.ok


def test_two_week_cycle_biweekly_lessons_take_turns():
    # 1-nji topar: 15 slot, her hepde 14 sapak + iki dersiň her biri iki hepdede bir.
    # Iki hepdede birler bir slotda nobatlaşyp bilýär (biri 1-nji, beýlekisi 2-nji hepde).
    weekly = lesson("weekly", 1, [1], 14)
    a = dataclasses.replace(lesson("a", 2, [1], 0), biweekly=1)
    b = dataclasses.replace(lesson("b", 3, [1], 0), biweekly=1)
    inp = dataclasses.replace(base_input([weekly, a, b]), weeks=2)
    r = solve(inp)
    assert r.ok, r.issues
    k = by_key(r)
    assert all(p.week is None for p in k["weekly"])
    assert len(k["a"]) == len(k["b"]) == 1
    assert {k["a"][0].week, k["b"][0].week} == {1, 2}
    # her hepdede topar bir slotda diňe bir sapakda
    for w in (1, 2):
        used = [p.slot_id for p in r.placements if p.week in (None, w)]
        assert len(used) == len(set(used)) == 15


def test_one_week_mode_counts_biweekly_as_weekly():
    r = solve(base_input([dataclasses.replace(lesson("a", 1, [1], 1), biweekly=1)]))
    assert r.ok and len(r.placements) == 2 and all(p.week is None for p in r.placements)
