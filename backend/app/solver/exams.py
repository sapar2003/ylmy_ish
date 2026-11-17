"""Synag raspisaniýesi (OR-Tools CP-SAT). Maglumat bazasyna bagly däl.

Gaty şertler: her synag bir gezek; uly we kiçi mugallym we topar bir wagtda diňe bir synagda; topar günde
`max_per_day`-dan köp synag tabşyrmaýar we synaglarynyň arasynda `rest_days` boş gün bolýar;
her wagtda ýeterlik laýyk otag bar.
Maslahat (`consultations`): her synagdan öňki iş güni 08:30-da uly mugallym topara maslahat berýär, şonuň üçin
möwsümiň ilkinji güni synag bolmaýar, toparyň maslahat gününde synagy bolmaýar we mugallymyň maslahaty onuň
şol günki 08:30-daky synagy bilen çaknyşmaýar.
Toparyň öz otagy (`fixed_room_id`) bolsa, synag şol otagda geçýär we otag bir wagtda bir synag üçin.
Ýumşak şertler: toparyň synaglary yzly-yzyna günlere düşmesin we deň aralykda bolsun (`spread_days`),
mugallymyň günde bir synagy bolsun.
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from ortools.sat.python import cp_model

from app.solver.engine import STATUS_NAMES, add_room_limits, assign_rooms
from app.solver.model import Room
from app.solver.precheck import eligible_rooms

W_NEXT_DAY = 10  # toparyň synagy öňki günki synagdan soň
W_TEACHER_SAME_DAY = 3  # mugallymyň bir günde ikinji synagy
W_LATE = 1  # her wagt belgisi üçin: ir synaglar gowy
W_SPREAD = 4  # toparyň iki synagynyň arasy `spread_days`-dan az


@dataclass(frozen=True)
class ExamSlot:
    id: int  # içki belgi
    day: date
    period_id: int
    number: int


@dataclass(frozen=True)
class ExamItem:
    key: str
    group_ids: tuple[int, ...]
    teacher_ids: tuple[int, ...]  # uly we kiçi mugallym
    size: int
    room_type_id: int | None = None
    faculty_ids: frozenset[int] = frozenset()
    label: str = ""
    examiner_id: int | None = None  # maslahaty berýän uly mugallym
    fixed_room_id: int | None = None  # toparyň öz otagy


@dataclass
class ExamInput:
    slots: list[ExamSlot]
    rooms: list[Room]
    exams: list[ExamItem]
    max_per_day: int = 1
    rest_days: int = 0
    consultations: bool = False
    spread_days: int = 0  # toparyň synaglarynyň arasynda islenýän boş gün (ýumşak)
    time_limit_seconds: float = 60
    workers: int = 8


@dataclass
class ExamPlacement:
    exam_key: str
    slot_id: int
    room_id: int | None


@dataclass
class ExamResult:
    ok: bool
    status: str
    placements: list[ExamPlacement] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    objective: float | None = None
    seconds: float = 0


def exam_precheck(inp: ExamInput) -> list[str]:
    issues: list[str] = []
    if not inp.slots:
        issues.append("Synag wagty ýok: möwsümiň senelerini, günlerini we wagtlaryny barlaň.")
        return issues
    days = sorted({s.day for s in inp.slots})
    # rest_days boş gün bilen bir toparyň tabşyryp biljek iň köp synag güni (gaty takyk däl, ýöne ýeterlik).
    usable_days, last = 0, None
    for d in days:
        if last is None or (d - last).days > inp.rest_days:
            usable_days, last = usable_days + 1, d
    per_group = defaultdict(int)
    per_teacher = defaultdict(int)
    for e in inp.exams:
        if e.fixed_room_id is None and not eligible_rooms(inp.rooms, e):
            issues.append(f"{e.label or e.key}: {e.size} talyp üçin laýyk otag (sygymy/görnüşi/fakulteti) ýok.")
        for g in e.group_ids:
            per_group[g] += 1
        for t in e.teacher_ids:
            per_teacher[t] += 1
    group_cap = usable_days * inp.max_per_day
    for g, n in per_group.items():
        if n > group_cap:
            issues.append(f"Topar id={g}: {n} synag bar, ýöne möwsümde iň köp {group_cap} synag goýup bolýar.")
    for t, n in per_teacher.items():
        if n > len(inp.slots):
            issues.append(f"Mugallym id={t}: {n} synag bar, ýöne diňe {len(inp.slots)} synag wagty bar.")
    return issues


def solve_exams(inp: ExamInput) -> ExamResult:
    started = time.monotonic()
    issues = exam_precheck(inp)
    if issues:
        return ExamResult(ok=False, status="precheck_failed", issues=issues, seconds=time.monotonic() - started)

    model = cp_model.CpModel()
    days = sorted({s.day for s in inp.slots})
    prev_day = {d: days[i - 1] if i else None for i, d in enumerate(days)}
    x = {}
    penalties = []
    by_slot = defaultdict(list)
    by_teacher_slot = defaultdict(list)
    by_teacher_day = defaultdict(list)
    by_group_slot = defaultdict(list)
    by_group_day = defaultdict(list)
    by_room_slot = defaultdict(list)
    consults = defaultdict(list)  # (mugallym, gün) -> şol gün maslahat bermeli synaglar
    slot_of = {(s.day, s.number): s.id for s in inp.slots}
    first_number = min(s.number for s in inp.slots)
    for i, e in enumerate(inp.exams):
        vars_ = []
        for s in inp.slots:
            if inp.consultations and prev_day[s.day] is None:
                continue  # maslahat güni ýok
            v = model.new_bool_var(f"e_{i}_{s.id}")
            x[i, s.id] = v
            vars_.append(v)
            by_slot[s.id].append((e, v))
            for t in e.teacher_ids:
                by_teacher_slot[t, s.id].append(v)
                by_teacher_day[t, s.day].append(v)
            for g in e.group_ids:
                by_group_slot[g, s.id].append(v)
                by_group_day[g, s.day].append(v)
            penalties.append(W_LATE * s.number * v)
            if e.fixed_room_id is not None:
                by_room_slot[e.fixed_room_id, s.id].append(v)
            if inp.consultations and e.examiner_id is not None:
                consults[e.examiner_id, prev_day[s.day]].append(v)
        model.add_exactly_one(vars_)

    for vars_ in (*by_teacher_slot.values(), *by_group_slot.values(), *by_room_slot.values()):
        model.add_at_most_one(vars_)
    # Mugallymyň maslahaty (08:30) onuň şol günki ilkinji wagtdaky synagy bilen çaknyşmaýar.
    for (t, d), cvars in consults.items():
        sid = slot_of.get((d, first_number))
        busy = by_teacher_slot.get((t, sid), []) if sid is not None else []
        if busy:
            k = len(cvars)
            model.add(sum(cvars) + k * sum(busy) <= k)
    for vars_ in by_teacher_day.values():
        if len(vars_) > 1:
            extra = model.new_int_var(0, len(vars_), "")
            model.add(extra >= sum(vars_) - 1)
            penalties.append(W_TEACHER_SAME_DAY * extra)

    groups = {g for g, _ in by_group_day}
    for g in groups:
        has_exam = {}
        for d in days:
            vars_ = by_group_day.get((g, d), [])
            model.add(sum(vars_) <= inp.max_per_day)
            flag = model.new_bool_var("")
            model.add(sum(vars_) >= 1).only_enforce_if(flag)
            model.add(sum(vars_) == 0).only_enforce_if(flag.Not())
            has_exam[d] = flag
        for i, d in enumerate(days):
            if inp.consultations and prev_day[d] is not None:  # maslahat güni synagsyz
                model.add_bool_or([has_exam[d].Not(), has_exam[prev_day[d]].Not()])
            for d2 in days[i + 1:]:
                gap = (d2 - d).days - 1  # arasyndaky boş günler
                if gap < inp.rest_days:
                    model.add_bool_or([has_exam[d].Not(), has_exam[d2].Not()])
                elif gap < inp.spread_days:
                    both = model.new_bool_var("")
                    model.add_bool_and([has_exam[d], has_exam[d2]]).only_enforce_if(both)
                    model.add_bool_or([has_exam[d].Not(), has_exam[d2].Not()]).only_enforce_if(both.Not())
                    penalties.append(W_SPREAD * (inp.spread_days - gap) * both)
                elif gap == 0:
                    both = model.new_bool_var("")
                    model.add_bool_and([has_exam[d], has_exam[d2]]).only_enforce_if(both)
                    model.add_bool_or([has_exam[d].Not(), has_exam[d2].Not()]).only_enforce_if(both.Not())
                    penalties.append(W_NEXT_DAY * both)

    fixed_rooms = {e.fixed_room_id for e in inp.exams if e.fixed_room_id is not None}
    free_rooms = [r for r in inp.rooms if r.id not in fixed_rooms]
    for here in by_slot.values():
        loose = [(e, v) for e, v in here if e.fixed_room_id is None]
        if loose:
            add_room_limits(model, free_rooms or inp.rooms, loose)

    model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(1.0, inp.time_limit_seconds)
    solver.parameters.num_workers = inp.workers
    status = solver.solve(model)
    status_name = STATUS_NAMES.get(status, str(status))
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        msg = (
            "Ähli şertleri kanagatlandyrýan synag raspisaniýesi ýok. Möwsümiň günlerini, synag wagtlaryny, "
            "dynç günlerini we otaglary barlaň."
            if status == cp_model.INFEASIBLE
            else "Wagt çäginde çözgüt tapylmady: wagt çägini artdyryň."
        )
        return ExamResult(ok=False, status=status_name, issues=[msg], seconds=time.monotonic() - started)

    chosen = defaultdict(list)
    for (i, sid), v in x.items():
        if solver.value(v):
            chosen[sid].append(i)
    placements, issues = [], []
    for sid, idxs in chosen.items():
        loose = {i: inp.exams[i] for i in idxs if inp.exams[i].fixed_room_id is None}
        rooms = assign_rooms(free_rooms or inp.rooms, loose) if loose else {}
        if rooms is None:
            issues.append(f"Synag wagty id={sid}: otaglary bölüp bolmady, synaglar otagsyz goýuldy.")
            rooms = {}
        placements += [
            ExamPlacement(inp.exams[i].key, sid, inp.exams[i].fixed_room_id or rooms.get(i)) for i in idxs
        ]
    return ExamResult(
        ok=True, status=status_name, placements=placements, issues=issues,
        objective=solver.objective_value, seconds=time.monotonic() - started,
    )
