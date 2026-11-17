"""Ýarymýyllyk synag: maslahat güni, toparyň öz otagy we Word faýlyndan okamak."""
from datetime import date, time, timedelta

from app.importers.exam_docx import parse_entries
from app.solver.exams import ExamInput, ExamItem, ExamSlot, solve_exams
from app.solver.model import Room


def _slots(start: date, n_days: int) -> list[ExamSlot]:
    slots, sid, d = [], 0, start
    while len({s.day for s in slots}) < n_days:
        if d.isoweekday() != 7:
            for number in (1, 2):
                sid += 1
                slots.append(ExamSlot(id=sid, day=d, period_id=number, number=number))
        d += timedelta(days=1)
    return slots


def test_consultation_rules_and_home_room():
    slots = _slots(date(2027, 1, 12), 8)
    rooms = [Room(id=1, capacity=30, room_type_id=1), Room(id=2, capacity=30, room_type_id=1)]
    exams = [
        ExamItem(key=f"g{g}-{k}", group_ids=(g,), teacher_ids=(10 + k, 20 + k), size=20, examiner_id=10 + k,
                 fixed_room_id=g)
        for g in (1, 2) for k in range(3)
    ]
    res = solve_exams(ExamInput(slots=slots, rooms=rooms, exams=exams, rest_days=1, consultations=True,
                                spread_days=3, time_limit_seconds=10, workers=2))
    assert res.ok, res.issues
    slot = {s.id: s for s in slots}
    days = sorted({s.day for s in slots})
    prev = {d: days[i - 1] for i, d in enumerate(days) if i}
    by_group = {}
    for p in res.placements:
        e = next(x for x in exams if x.key == p.exam_key)
        assert p.room_id == e.fixed_room_id  # öz otagynda
        d = slot[p.slot_id].day
        assert d != days[0]  # ilkinji gün maslahat güni ýok
        by_group.setdefault(e.group_ids[0], []).append(d)
    for ds in by_group.values():
        ds.sort()
        for a, b in zip(ds, ds[1:]):
            assert prev[b] != a and (b - a).days >= 2  # maslahat güni synagsyz


def test_parse_run_together_cell():
    text = ("Maslahat 0830Fizikauly mug.M.Öwlýagulowa Synag 1000Maglumat howpsuzlygyuly mug.G.Arrykowa"
            "mug.-öwr.M.Annamyradow(V-106) Synag 0830Obýekte gönükdirilen programmirlemeuly mug.M.Çüriýew "
            "mug.Agajykowa")
    a, b, c = parse_entries(text, date(2027, 1, 14))
    assert (a.kind, a.start, a.subject, a.teachers[0].surname) == ("consult", time(8, 30), "Fizika", "Öwlýagulowa")
    assert (b.kind, b.start, b.subject, b.room) == ("exam", time(10, 0), "Maglumat howpsuzlygy", "V-106")
    assert [(t.rank, t.initial, t.surname) for t in b.teachers] == [
        ("uly mug.", "G", "Arrykowa"), ("mug.-öwr.", "M", "Annamyradow")]
    assert c.subject == "Obýekte gönükdirilen programmirleme"
    assert [(t.initial, t.surname) for t in c.teachers] == [("M", "Çüriýew"), (None, "Agajykowa")]
