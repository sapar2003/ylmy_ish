"""OR-Tools CP-SAT bilen iki tapgyrly raspisaniýe:

1. Wagt: her sapak üçin haýsy slotlarda geçjekdigi (gaty we ýumşak çäklendirmeler).
2. Otag: her slotda geçýän sapaklara otag bölmek (sygym, görnüş, boş galýan ýer az bolsun).

Birinji tapgyrda otaglaryň sany hem hasaba alynýar (her slotda uly sapaklar üçin ýeterlik uly otag bolmaly),
şonuň üçin ikinji tapgyr köplenç ilkinji synanyşykda çözülýär.
"""
import time
from collections import defaultdict

from ortools.sat.python import cp_model

from app.solver.model import Placement, SolverInput, SolverResult
from app.solver.precheck import eligible_rooms, precheck, room_allowed, teacher_slots

# Ýumşak çäklendirmeleriň agramy (jerime ballary).
W_SAME_DAY = 30  # bir ders bir günde iki gezek
W_PREFERRED = 5  # mugallymyň isleýän wagty (bonus)
W_LATE = 1  # her sapak belgisi üçin: ir sapaklar gowy, gün gysga bolsun

STATUS_NAMES = {
    cp_model.OPTIMAL: "optimal",
    cp_model.FEASIBLE: "feasible",
    cp_model.INFEASIBLE: "infeasible",
    cp_model.MODEL_INVALID: "model_invalid",
    cp_model.UNKNOWN: "unknown",
}


def add_room_limits(model: cp_model.CpModel, rooms: list, here: list) -> None:
    """Bir wagtda geçýän sapaklar/synaglar üçin otaglaryň sanyny hasaba alýar.

    `here`: [(sapak ýa-da synag, bool var)]. Her ulanyp bolýan otaglar toplumy A we sygym çägi c üçin:
    diňe A-nyň içindäki otaglara sygýan, c-den uly sapaklaryň sany A-daky c-den uly otaglardan köp däl.
    Bu takyk bölüşik däl (ony ikinji tapgyr edýär), ýöne köplenç ýeterlik.
    """
    model.add(sum(v for _, v in here) <= len(rooms))
    allowed = {}  # otag talaby (görnüşi, fakultetleri) -> ulanyp bolýan otaglar
    for item, _ in here:
        need = (item.room_type_id, item.faculty_ids)
        if need not in allowed:
            allowed[need] = frozenset(r.id for r in rooms if room_allowed(r, item))
    capacity = {r.id: r.capacity for r in rooms}
    for room_set in set(allowed.values()) | {frozenset(capacity)}:
        inside = [(item, v) for item, v in here if allowed[item.room_type_id, item.faculty_ids] <= room_set]
        for c in sorted({item.size for item, _ in inside}):
            big = [v for item, v in inside if item.size >= c]
            model.add(sum(big) <= sum(1 for rid in room_set if capacity[rid] >= c))


def _solve_times(inp: SolverInput, time_limit: float):
    model = cp_model.CpModel()
    slot_by_id = {s.id: s for s in inp.slots}
    x: dict[tuple[int, int], cp_model.IntVar] = {}  # (sapak indeksi, slot id) -> bool
    penalties = []

    by_slot = defaultdict(list)  # slot id -> [(sapak indeksi, var)]
    by_teacher_slot = defaultdict(list)
    by_teacher_day = defaultdict(list)
    by_group_slot = defaultdict(list)  # toparyň umumy sapaklary
    by_subgroup_slot = defaultdict(list)

    for i, lesson in enumerate(inp.lessons):
        teacher = inp.teachers[lesson.teacher_id]
        per_day = defaultdict(list)
        for sid in sorted(teacher_slots(inp, lesson)):
            v = model.new_bool_var(f"x_{i}_{sid}")
            x[i, sid] = v
            slot = slot_by_id[sid]
            by_slot[sid].append((i, v))
            by_teacher_slot[lesson.teacher_id, sid].append(v)
            by_teacher_day[lesson.teacher_id, slot.weekday].append(v)
            per_day[slot.weekday].append(v)
            if lesson.subgroup_id is None:
                for g in lesson.group_ids:
                    by_group_slot[g, sid].append(v)
            else:
                by_subgroup_slot[lesson.subgroup_id, sid].append(v)
            penalties.append(W_LATE * slot.number * v)
            if sid in teacher.preferred:
                penalties.append(-W_PREFERRED * v)
        model.add(sum(v for vs in per_day.values() for v in vs) == lesson.per_week)

        # Bir dersi bir günde iki gezek goýmazlyk (mümkin bolsa).
        for day, day_vars in per_day.items():
            if len(day_vars) > 1:
                extra = model.new_int_var(0, len(day_vars), f"same_day_{i}_{day}")
                model.add(extra >= sum(day_vars) - 1)
                penalties.append(W_SAME_DAY * extra)

    # Mugallym bir wagtda diňe bir ýerde (ähli fakultetler boýunça).
    for vars_ in by_teacher_slot.values():
        model.add_at_most_one(vars_)

    # Topar: umumy sapak we her kiçi toparyň sapagy bir wagtda bolup bilmez.
    # Iki kiçi toparyň sapaklary bolsa bir wagtda geçip biler.
    group_of_subgroup = {sg: g for g, subs in inp.subgroups_of.items() for sg in subs}
    group_slot_keys = set(by_group_slot) | {(group_of_subgroup[sg], sid) for sg, sid in by_subgroup_slot}
    for g, sid in group_slot_keys:
        common = by_group_slot.get((g, sid), [])
        subs = inp.subgroups_of.get(g, [])
        if not subs:
            model.add_at_most_one(common)
        for sg in subs:
            model.add_at_most_one(common + by_subgroup_slot.get((sg, sid), []))

    # Mugallymyň günlük çägi.
    for (tid, _day), vars_ in by_teacher_day.items():
        limit = inp.teachers[tid].max_per_day
        if limit is not None:
            model.add(sum(vars_) <= limit)

    for here in by_slot.values():
        add_room_limits(model, inp.rooms, [(inp.lessons[i], v) for i, v in here])

    model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(1.0, time_limit)
    solver.parameters.num_workers = inp.workers
    status = solver.solve(model)
    return solver, status, x


def assign_rooms(rooms: list, items: dict[int, object]) -> dict[int, int] | None:
    """Bir wagtda geçýän sapaklara/synaglara otag bölýär; boş galýan orunlary azaldýar.

    `items`: {indeks: sapak ýa-da synag}; netije {indeks: otag id}.
    """
    model = cp_model.CpModel()
    y = {}
    for i, item in items.items():
        options = eligible_rooms(rooms, item)
        if not options:
            return None
        for r in options:
            y[i, r.id] = model.new_bool_var(f"y_{i}_{r.id}")
        model.add_exactly_one(y[i, r.id] for r in options)
    by_room = defaultdict(list)
    for (i, rid), v in y.items():
        by_room[rid].append(v)
    for vars_ in by_room.values():
        model.add_at_most_one(vars_)
    cap = {r.id: r.capacity for r in rooms}
    model.minimize(sum((cap[rid] - items[i].size) * v for (i, rid), v in y.items()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    if solver.solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    return {i: rid for (i, rid), v in y.items() if solver.value(v)}


def solve(inp: SolverInput) -> SolverResult:
    started = time.monotonic()
    issues = precheck(inp)
    if issues:
        return SolverResult(ok=False, status="precheck_failed", issues=issues, seconds=time.monotonic() - started)

    solver, status, x = _solve_times(inp, inp.time_limit_seconds)
    status_name = STATUS_NAMES.get(status, str(status))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        msg = (
            "Ähli şertleri kanagatlandyrýan raspisaniýe ýok. Mugallymlaryň boş wagtyny, smenalary "
            "we otaglaryň sanyny barlaň."
            if status == cp_model.INFEASIBLE
            else "Wagt çäginde çözgüt tapylmady: wagt çägini artdyryň."
        )
        return SolverResult(ok=False, status=status_name, issues=[msg], seconds=time.monotonic() - started)

    chosen = defaultdict(list)  # slot id -> [sapak indeksi]
    for (i, sid), v in x.items():
        if solver.value(v):
            chosen[sid].append(i)

    placements, issues = [], []
    for sid, idxs in chosen.items():
        rooms = assign_rooms(inp.rooms, {i: inp.lessons[i] for i in idxs})
        if rooms is None:
            issues.append(f"Slot id={sid}: otaglary bölüp bolmady, sapaklar otagsyz goýuldy.")
            rooms = {}
        placements += [Placement(inp.lessons[i].key, sid, rooms.get(i)) for i in idxs]

    return SolverResult(
        ok=True,
        status=status_name,
        placements=placements,
        issues=issues,
        objective=solver.objective_value,
        seconds=time.monotonic() - started,
    )
