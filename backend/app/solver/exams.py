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
W_RELAX = 300  # ýumşadylan gaty düzgün (maslahat güni, boş gün) bozulsa
W_STAY = 6  # öňki raspisaniýedäki ýerinden süýşen synag (beýlekilere päsgel bermezlik üçin)
W_EARLY = 60  # "ilkinji günlere" toparyň synagy her gün giç düşse


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
    weekdays: frozenset[int] | None = None  # diňe şu hepde günlerinde
    latest_day: date | None = None  # iň giç şu güne çenli
    compact: bool = False  # ilkinji günlere: maslahat güni → synag güni → maslahat güni ... goşmaça boş günsüz


@dataclass
class ExamInput:
    slots: list[ExamSlot]
    rooms: list[Room]
    exams: list[ExamItem]
    max_per_day: int = 1
    rest_days: int = 0
    consultations: bool = False
    spread_days: int = 0  # toparyň synaglarynyň arasynda islenýän boş gün (ýumşak)
    # Beýleki möwsümleriň (meselem, başga fakultetiň) şol günlerdäki synaglary: (mugallym/otag, gün, wagt belgisi)
    busy_teachers: frozenset = frozenset()
    busy_rooms: frozenset = frozenset()
    previous: dict = field(default_factory=dict)  # öňki raspisaniýe: synag açary -> (gün, wagt belgisi)
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


def _strict_capacity(inp: ExamInput, days: list) -> int:
    """Bir toparyň ähli gaty şertlerde tabşyryp biljek iň köp synag sany: rest_days boş gün, maslahat bolsa
    öňki iş güni synagsyz we ilkinji gün synag ýok (iň ir günleri açgözlük bilen saýlamak takyk netije berýär)."""
    usable, last = 0, None
    for i, d in enumerate(days):
        if inp.consultations and (i == 0 or days[i - 1] == last):
            continue
        if last is None or (d - last).days > inp.rest_days:
            usable, last = usable + 1, d
    return usable if inp.consultations else usable * inp.max_per_day


def _group_names(inp: ExamInput) -> dict[int, str]:
    return {e.group_ids[0]: e.label.split(" · ")[0] for e in inp.exams if len(e.group_ids) == 1 and e.label}


def _per_group(inp: ExamInput) -> dict[int, int]:
    out = defaultdict(int)
    for e in inp.exams:
        for g in e.group_ids:
            out[g] += 1
    return out


def exam_precheck(inp: ExamInput) -> list[str]:
    """Hiç hili ýumşatmak bilen hem çözüp bolmaýan ýagdaýlar (raspisaniýe düzülmez)."""
    issues: list[str] = []
    if not inp.slots:
        issues.append("Synag wagty ýok: möwsümiň senelerini, günlerini we wagtlaryny barlaň.")
        return issues
    days = sorted({s.day for s in inp.slots})
    per_teacher = defaultdict(int)
    for e in inp.exams:
        if e.fixed_room_id is None and not eligible_rooms(inp.rooms, e):
            issues.append(f"{e.label or e.key}: {e.size} talyp üçin laýyk otag (sygymy/görnüşi/fakulteti) ýok.")
        for t in e.teacher_ids:
            per_teacher[t] += 1
    names = _group_names(inp)
    cap = len(days) * inp.max_per_day
    strict = _strict_capacity(inp, days) if inp.consultations else None
    for g, n in _per_group(inp).items():
        if strict is not None and n > strict:
            issues.append(
                f"{names.get(g, f'Topar id={g}')}: {n} synag bar. Her synagdan öň aýry maslahat güni gerek "
                f"(maslahat bilen synag bir günde bolmaýar), şonuň üçin iň az {2 * n} iş güni gerek, möwsümde "
                f"{len(days)} iş güni bar (iň köp {strict} synag sygýar). Möwsümi iň az {max(1, 2 * n - len(days))} "
                f"iş güni uzaldyň ýa-da synag sanyny azaldyň.")
            continue
        if n > cap:
            issues.append(f"{names.get(g, f'Topar id={g}')}: {n} synag bar, ýöne möwsümde diňe {len(days)} synag "
                          f"güni bar. Möwsümi iň az {n - len(days)} iş güni uzaldyň.")
    deadline: dict[int, date] = {}
    for e in inp.exams:
        if e.latest_day:
            for g in e.group_ids:
                deadline[g] = min(deadline.get(g, e.latest_day), e.latest_day)
    per_group = _per_group(inp)
    for g, last in deadline.items():
        window = [d for d in days if d <= last]
        cap = _strict_capacity(inp, window) if inp.consultations else len(window)
        if per_group[g] > cap:
            issues.append(f"{names.get(g, f'Topar id={g}')}: {per_group[g]} synag {last:%d.%m} çenli gutarmaly, "
                          f"ýöne şol güne çenli iň köp {cap} synag sygýar. Senäni giçräk ediň.")
    for t, n in per_teacher.items():
        if n > len(inp.slots):
            issues.append(f"Mugallym id={t}: {n} synag bar, ýöne diňe {len(inp.slots)} synag wagty bar.")
    return issues


def strict_warnings(inp: ExamInput) -> list[str]:
    """Gaty düzgünlerde ýerleşmeýän toparlar (bu toparlar üçin düzgünler ýumşadylýar)."""
    if not inp.slots:
        return []
    days = sorted({s.day for s in inp.slots})
    cap = _strict_capacity(inp, days)
    names = _group_names(inp)
    why = "her synagdan öň maslahat güni we " if inp.consultations else ""
    out = []
    for g, n in _per_group(inp).items():
        if n > cap:
            need = 2 * n + 1 if inp.consultations else n * (inp.rest_days + 1)
            out.append(f"{names.get(g, f'Topar id={g}')}: {n} synag bar, {why}synaglaryň arasynda boş gün bilen "
                       f"möwsümde iň köp {cap} synag sygýar (takmynan {need} iş güni gerek, möwsümde {len(days)}).")
    return out


def solve_exams(inp: ExamInput) -> ExamResult:
    """Ilki ähli düzgünler gaty; çözgüt ýok bolsa, toparyň maslahat güni we boş gün düzgünleri ýumşadylýar."""
    started = time.monotonic()
    issues = exam_precheck(inp)
    if issues:
        return ExamResult(ok=False, status="precheck_failed", issues=issues, seconds=time.monotonic() - started)
    warnings = strict_warnings(inp)
    if not warnings:
        res = _solve(inp, relaxed=False, started=started)
        if res.ok or res.status != "infeasible":
            return res
    relaxed = _solve(inp, relaxed=True, started=started)
    if relaxed.ok:
        relaxed.issues = (warnings or ["Ähli düzgünleri birden kanagatlandyryp bolmady."]) + relaxed.issues
        return relaxed
    busy = defaultdict(int)
    for e in inp.exams:
        for t in e.teacher_ids:
            busy[t] += 1
    top = sorted(busy.items(), key=lambda kv: -kv[1])[:3]
    relaxed.issues = warnings + [
        "Toparlaryň düzgünleri ýumşadylanda hem mugallymlaryň we otaglaryň çaknyşmazlygy bilen raspisaniýe "
        "düzüp bolmady. Iň köp synagy bolan mugallymlar: " + ", ".join(f"id={t} ({n} synag)" for t, n in top)
        + ". Möwsümi uzaldyň, synag wagtyny goşuň ýa-da kiçi mugallymlary üýtgediň."
    ]
    return relaxed


def _solve(inp: ExamInput, relaxed: bool, started: float) -> ExamResult:
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
    numbers = {s.number for s in inp.slots}
    day_index = {d: i for i, d in enumerate(days)}
    compact_groups = {g for e in inp.exams if e.compact for g in e.group_ids}
    violations = []  # ýumşadylan düzgünler: (topar, düşündiriş, bool var)
    shared = defaultdict(set)
    for e in inp.exams:
        if e.fixed_room_id is not None:
            shared[e.fixed_room_id] |= set(e.group_ids)
    fixed = {i: (e.fixed_room_id if not (relaxed and len(shared[e.fixed_room_id]) > 1) else None)
             for i, e in enumerate(inp.exams)}
    for i, e in enumerate(inp.exams):
        vars_ = []
        for s in inp.slots:
            if inp.consultations and prev_day[s.day] is None:
                continue  # maslahat güni ýok (bu düzgün hiç haçan ýumşadylmaýar)
            if e.weekdays and s.day.isoweekday() not in e.weekdays:
                continue
            if e.latest_day and s.day > e.latest_day:
                continue
            if any((t, s.day, s.number) in inp.busy_teachers for t in e.teacher_ids):
                continue  # mugallym başga möwsümiň synagynda
            if (inp.consultations and e.examiner_id is not None
                    and (e.examiner_id, prev_day[s.day], first_number) in inp.busy_teachers):
                continue  # maslahat wagty mugallym başga synagda
            if fixed[i] is not None and (fixed[i], s.day, s.number) in inp.busy_rooms:
                continue
            v = model.new_bool_var(f"e_{i}_{s.id}")
            if inp.previous.get(e.key) not in (None, (s.day, s.number)):
                penalties.append(W_STAY * v)
            if e.compact:
                penalties.append(W_EARLY * day_index[s.day] * v)
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
            if fixed[i] is not None:
                by_room_slot[fixed[i], s.id].append(v)
            if inp.consultations and e.examiner_id is not None and prev_day[s.day] is not None:
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
        def soft_or_hard(a, b, what, g=g):
            if not relaxed:
                model.add_bool_or([a.Not(), b.Not()])
                return
            both = model.new_bool_var("")
            model.add_bool_and([a, b]).only_enforce_if(both)
            model.add_bool_or([a.Not(), b.Not()]).only_enforce_if(both.Not())
            penalties.append(W_RELAX * both)
            violations.append((g, what, both))

        for i, d in enumerate(days):
            if inp.consultations and prev_day[d] is not None:  # maslahat güni synagsyz (hemişe gaty)
                model.add_bool_or([has_exam[d].Not(), has_exam[prev_day[d]].Not()])
            for d2 in days[i + 1:]:
                gap = (d2 - d).days - 1  # arasyndaky boş günler
                if gap < inp.rest_days:
                    if not (inp.consultations and prev_day[d2] == d):  # ýokarda eýýäm goşuldy
                        soft_or_hard(has_exam[d], has_exam[d2], f"{d:%d.%m}–{d2:%d.%m} arasynda boş gün ýok")
                elif gap < inp.spread_days and g not in compact_groups:  # "ilkinji günler" toparyna däl
                    both = model.new_bool_var("")
                    model.add_bool_and([has_exam[d], has_exam[d2]]).only_enforce_if(both)
                    model.add_bool_or([has_exam[d].Not(), has_exam[d2].Not()]).only_enforce_if(both.Not())
                    penalties.append(W_SPREAD * (inp.spread_days - gap) * both)
                elif gap == 0:
                    both = model.new_bool_var("")
                    model.add_bool_and([has_exam[d], has_exam[d2]]).only_enforce_if(both)
                    model.add_bool_or([has_exam[d].Not(), has_exam[d2].Not()]).only_enforce_if(both.Not())
                    penalties.append(W_NEXT_DAY * both)

    fixed_rooms = {r for r in fixed.values() if r is not None}
    free_rooms = [r for r in inp.rooms if r.id not in fixed_rooms]
    slot_by_id = {s.id: s for s in inp.slots}

    def open_rooms(sid):  # başga möwsümde eýelenmedik otaglar
        s = slot_by_id[sid]
        return [r for r in (free_rooms or inp.rooms) if (r.id, s.day, s.number) not in inp.busy_rooms]

    index = {id(e): i for i, e in enumerate(inp.exams)}
    for sid, here in by_slot.items():
        loose = [(e, v) for e, v in here if fixed[index[id(e)]] is None]
        if loose:
            add_room_limits(model, open_rooms(sid), loose)

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
        if status == cp_model.INFEASIBLE:
            status_name = "infeasible"
        return ExamResult(ok=False, status=status_name, issues=[msg], seconds=time.monotonic() - started)

    chosen = defaultdict(list)
    for (i, sid), v in x.items():
        if solver.value(v):
            chosen[sid].append(i)
    placements, issues = [], []
    if relaxed:
        names = _group_names(inp)
        broken = defaultdict(list)
        for g, what, v in violations:
            if solver.value(v):
                broken[g].append(what)
        for g, whats in broken.items():
            issues.append(f"{names.get(g, f'Topar id={g}')}: düzgün ýumşadyldy — " + "; ".join(sorted(set(whats))))
    if compact_groups:
        names = _group_names(inp)
        slot_day = {s.id: s.day for s in inp.slots}
        for g in compact_groups:
            got = sorted(day_index[slot_day[sid]] for sid, idxs in chosen.items() for i in idxs
                         if g in inp.exams[i].group_ids)
            dates = ", ".join(f"{days[k]:%d.%m}" for k in got)
            step = 2 if inp.consultations else 1  # maslahat güni, synag güni, maslahat güni...
            first = 1 if inp.consultations else 0
            if got and got != list(range(first, first + step * len(got), step)):
                issues.append(f"{names.get(g, f'Topar id={g}')}: synaglar iň ir günlere goýuldy, ýöne mugallym "
                              f"ýa-da otag çaknyşmasy sebäpli arasynda goşmaça boş gün galdy: {dates}")
    for sid, idxs in chosen.items():
        loose = {i: inp.exams[i] for i in idxs if fixed[i] is None}
        rooms = assign_rooms(open_rooms(sid), loose) if loose else {}
        if rooms is None:
            issues.append(f"Synag wagty id={sid}: otaglary bölüp bolmady, synaglar otagsyz goýuldy.")
            rooms = {}
        placements += [
            ExamPlacement(inp.exams[i].key, sid, fixed[i] or rooms.get(i)) for i in idxs
        ]
    return ExamResult(
        ok=True, status=status_name, placements=placements, issues=issues,
        objective=solver.objective_value, seconds=time.monotonic() - started,
    )
