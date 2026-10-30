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
W_GAP = 50  # toparyň gününde sapaklaryň arasynda boş jübüt ("penjire")
W_SINGLE_DAY = 40  # toparyň gününde diňe 1 jübüt
W_EMPTY_DAY = 10  # toparyň sapaksyz güni (ýük azlygynda bolup biler, ýöne günlere paýlamak gowy)

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


def weekly_count(inp: SolverInput, lesson) -> int:
    """Her hepde geçýän sapak sany. Bir hepdelik raspisaniýede iki hepdede birler hem şoňa goşulýar."""
    return lesson.per_week + (lesson.biweekly if inp.weeks == 1 else 0)


def time_ranks(slots) -> dict[int, int]:
    """slot id -> günüň içindäki wagt orny (1 = iň ir). Dürli smenalaryň bir wagtdaky slotlary
    (meselem, irden 3-nji we öýlän 1-nji jübüt, ikisi hem 11:40) birmeňzeş orunda bolýar."""
    key = {s.id: (s.start, 0) if s.start else (0, s.number) for s in slots}
    order = sorted(set(key.values()))
    return {sid: order.index(k) + 1 for sid, k in key.items()}


def _group_day_shape(model, slot_by_id, rank, by_group_slot, by_subgroup_slot, subgroups_of) -> list:
    """Talyplaryň gününiň görnüşi üçin ýumşak çäklendirmeler:
    - sapaklaryň arasynda boş jübüt bolmasyn (penjire), wagt boýunça (smenalar garyşsa hem);
    - günde iň az 2 jübüt bolsun: 1 jübütli gün güýçli jerimelenýär, boş gün az (ýük az bolsa
      käbir gün boş galyp biler, ýöne 1 jübütli günden gowy).
    Kiçi topary bar toparda her kiçi toparyň güni aýratyn barlanýar (umumy sapaklar + öz sapaklary):
    1-nji kiçi topar 1-nji jübütde, 2-nji kiçi topar 2-nji jübütde okasa, ikisinde hem penjire bar.
    """
    timelines = defaultdict(list)  # okaýan (topar ýa-da kiçi topar) -> [(hepde, slot, var-lar)]
    for (g, w, sid), vs in by_group_slot.items():
        for who in [("sg", sg) for sg in subgroups_of.get(g, [])] or [("g", g)]:
            timelines[who].append((w, sid, vs))
    for (sg, w, sid), vs in by_subgroup_slot.items():
        timelines["sg", sg].append((w, sid, vs))
    busy = defaultdict(list)  # (okaýan, hepde, gün, wagt orny) -> sapak var-lary
    for who, items in timelines.items():
        for w, sid, vs in items:
            busy[who, w, slot_by_id[sid].weekday, rank[sid]] += vs
    days = defaultdict(list)  # (okaýan, hepde, gün) -> [(wagt orny, eýelenen var)]
    for (who, w, day, r), vs in busy.items():
        occ = model.new_bool_var(f"busy_{who}_{w}_{day}_{r}")
        model.add_max_equality(occ, vs)
        days[who, w, day].append((r, occ))

    penalties = []
    for key, items in days.items():
        items.sort(key=lambda t: t[0])
        occ = [v for _, v in items]
        any_lesson = model.new_bool_var(f"day_{key}")
        model.add_max_equality(any_lesson, occ)
        single = model.new_bool_var(f"single_{key}")
        model.add(single >= 2 * any_lesson - sum(occ))  # diňe sapak sany 1 bolanda 1
        empty = model.new_bool_var(f"empty_{key}")
        model.add(empty >= 1 - any_lesson)
        penalties += [W_SINGLE_DAY * single, W_EMPTY_DAY * empty]
        for j in range(1, len(occ) - 1):  # j-nji jübüt boş, öňünde we yzynda sapak bar bolsa -> penjire
            before = model.new_bool_var(f"before_{key}_{j}")
            after = model.new_bool_var(f"after_{key}_{j}")
            model.add_max_equality(before, occ[:j])
            model.add_max_equality(after, occ[j + 1:])
            gap = model.new_bool_var(f"gap_{key}_{j}")
            model.add(gap >= before + after - occ[j] - 1)
            penalties.append(W_GAP * gap)
    return penalties


def _solve_times(inp: SolverInput, time_limit: float):
    """Wagt tapgyry. Iki hepdelik raspisaniýede (inp.weeks == 2) her wagt "hepde + slot" jübüti:
    her hepde geçýän sapak (x) iki hepdäniň şol slotuny hem tutýar, iki hepdede birki (y) diňe bir hepdäňkini.
    """
    model = cp_model.CpModel()
    slot_by_id = {s.id: s for s in inp.slots}
    rank = time_ranks(inp.slots)
    weeks = range(1, inp.weeks + 1)
    x: dict[tuple[int, int], cp_model.IntVar] = {}  # (sapak, slot) -> her hepde
    y: dict[tuple[int, int, int], cp_model.IntVar] = {}  # (sapak, hepde, slot) -> diňe şol hepde
    penalties = []

    by_slot = defaultdict(list)  # (hepde, slot) -> [(sapak indeksi, var)]
    by_teacher_slot = defaultdict(list)
    by_teacher_day = defaultdict(list)
    by_group_slot = defaultdict(list)  # toparyň umumy sapaklary
    by_subgroup_slot = defaultdict(list)

    for i, lesson in enumerate(inp.lessons):
        teacher = inp.teachers[lesson.teacher_id]
        every_week = weekly_count(inp, lesson)
        biweekly = lesson.biweekly if inp.weeks == 2 else 0
        per_day = defaultdict(list)  # (hepde, gün) -> var
        own_x, own_y = [], defaultdict(list)
        for sid in sorted(teacher_slots(inp, lesson)):
            slot = slot_by_id[sid]
            occupies = []  # (hepde, var)
            if every_week:
                v = model.new_bool_var(f"x_{i}_{sid}")
                x[i, sid] = v
                own_x.append(v)
                occupies += [(w, v) for w in weeks]
                penalties.append(W_LATE * rank[sid] * v)
                if sid in teacher.preferred:
                    penalties.append(-W_PREFERRED * v)
            for w in weeks if biweekly else ():
                v = model.new_bool_var(f"y_{i}_{w}_{sid}")
                y[i, w, sid] = v
                own_y[w].append(v)
                occupies.append((w, v))
                penalties.append(W_LATE * rank[sid] * v)
            for w, v in occupies:
                by_slot[w, sid].append((i, v))
                by_teacher_slot[lesson.teacher_id, w, sid].append(v)
                by_teacher_day[lesson.teacher_id, w, slot.weekday].append(v)
                per_day[w, slot.weekday].append(v)
                if lesson.subgroup_id is None:
                    for g in lesson.group_ids:
                        by_group_slot[g, w, sid].append(v)
                else:
                    by_subgroup_slot[lesson.subgroup_id, w, sid].append(v)
        if every_week:
            model.add(sum(own_x) == every_week)
        if biweekly:
            model.add(sum(v for vs in own_y.values() for v in vs) == biweekly)
            for vs in own_y.values():  # iki hepdä deň paýlamak
                model.add(sum(vs) <= (biweekly + 1) // 2)

        # Bir dersi bir günde iki gezek goýmazlyk (mümkin bolsa).
        for key, day_vars in per_day.items():
            if len(day_vars) > 1:
                extra = model.new_int_var(0, len(day_vars), f"same_day_{i}_{key}")
                model.add(extra >= sum(day_vars) - 1)
                penalties.append(W_SAME_DAY * extra)

    # Mugallym bir wagtda diňe bir ýerde (ähli fakultetler boýunça).
    for vars_ in by_teacher_slot.values():
        model.add_at_most_one(vars_)

    # Topar: umumy sapak we her kiçi toparyň sapagy bir wagtda bolup bilmez.
    # Iki kiçi toparyň sapaklary bolsa bir wagtda geçip biler.
    group_of_subgroup = {sg: g for g, subs in inp.subgroups_of.items() for sg in subs}
    group_slot_keys = set(by_group_slot) | {(group_of_subgroup[sg], w, sid) for sg, w, sid in by_subgroup_slot}
    for g, w, sid in group_slot_keys:
        common = by_group_slot.get((g, w, sid), [])
        subs = inp.subgroups_of.get(g, [])
        if not subs:
            model.add_at_most_one(common)
        for sg in subs:
            model.add_at_most_one(common + by_subgroup_slot.get((sg, w, sid), []))

    penalties += _group_day_shape(model, slot_by_id, rank, by_group_slot, by_subgroup_slot, inp.subgroups_of)

    # Mugallymyň günlük çägi.
    for (tid, _w, _day), vars_ in by_teacher_day.items():
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
    return solver, status, x, y


def assign_rooms(rooms: list, items: dict, clashes: list[list] | None = None) -> dict | None:
    """Bir wagtda geçýän sapaklara/synaglara otag bölýär; boş galýan orunlary azaldýar.

    `items`: {açar: sapak ýa-da synag}; netije {açar: otag id}.
    `clashes`: bir otagy paýlaşyp bilmeýän açarlaryň toparlary (adaty: hemmesi bir topar). Iki hepdelik
    raspisaniýede her hepde aýry topar: her hepde geçýän sapak ikisinde hem bar, şonuň üçin otagy üýtgemeýär.
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
    for keys in clashes or [list(items)]:
        by_room = defaultdict(list)
        for i in keys:
            for r in rooms:
                if (i, r.id) in y:
                    by_room[r.id].append(y[i, r.id])
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

    solver, status, x, y = _solve_times(inp, inp.time_limit_seconds)
    status_name = STATUS_NAMES.get(status, str(status))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        msg = (
            "Ähli şertleri kanagatlandyrýan raspisaniýe ýok. Mugallymlaryň boş wagtyny, smenalary "
            "we otaglaryň sanyny barlaň."
            if status == cp_model.INFEASIBLE
            else "Wagt çäginde çözgüt tapylmady: wagt çägini artdyryň."
        )
        return SolverResult(ok=False, status=status_name, issues=[msg], seconds=time.monotonic() - started)

    chosen = defaultdict(list)  # slot id -> [(sapak indeksi, hepde ýa-da None)]
    for (i, sid), v in x.items():
        if solver.value(v):
            chosen[sid].append((i, None))
    for (i, w, sid), v in y.items():
        if solver.value(v):
            chosen[sid].append((i, w))

    placements, issues = [], []
    for sid, keys in chosen.items():
        clashes = [[k for k in keys if k[1] in (None, w)] for w in range(1, inp.weeks + 1)]
        rooms = assign_rooms(inp.rooms, {k: inp.lessons[k[0]] for k in keys}, clashes)
        if rooms is None:
            issues.append(f"Slot id={sid}: otaglary bölüp bolmady, sapaklar otagsyz goýuldy.")
            rooms = {}
        placements += [Placement(inp.lessons[i].key, sid, rooms.get((i, w)), w) for i, w in keys]

    return SolverResult(
        ok=True,
        status=status_name,
        placements=placements,
        issues=issues,
        objective=solver.objective_value,
        seconds=time.monotonic() - started,
    )
