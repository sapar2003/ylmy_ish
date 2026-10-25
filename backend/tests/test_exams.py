from collections import Counter
from datetime import date, timedelta

from app.solver import Room
from app.solver.exams import ExamInput, ExamItem, ExamSlot, solve_exams
from tests.factories import make_basics, post

MONDAY = date(2026, 11, 2)


def slots(days=5, periods=2):
    return [
        ExamSlot(id=d * 10 + p, day=MONDAY + timedelta(days=d), period_id=p, number=p)
        for d in range(days) for p in range(1, periods + 1)
    ]


def exam(key, groups, teachers, size=20, faculties=()):
    return ExamItem(key=key, group_ids=tuple(groups), teacher_ids=tuple(teachers), size=size,
                    faculty_ids=frozenset(faculties))


def solve(exams, rooms=None, **kw):
    inp = ExamInput(slots=kw.pop("slots", slots()), rooms=rooms or [Room(1, 30, 1), Room(2, 30, 1)],
                    exams=exams, time_limit_seconds=10, workers=4, **kw)
    return inp, solve_exams(inp)


def test_group_one_exam_per_day_and_teachers_not_double_booked():
    exams = [exam(f"g1-{i}", [1], [i, 10 + i]) for i in range(4)] + [exam("g2-0", [2], [0, 10])]
    inp, r = solve(exams)
    assert r.ok, r.issues
    day = {s.id: s.day for s in inp.slots}
    g1_days = [day[p.slot_id] for p in r.placements if p.exam_key.startswith("g1")]
    assert len(set(g1_days)) == 4
    # 0-njy we 10-njy mugallymlar iki synagda: bir wagtda bolup bilmez.
    both = [p.slot_id for p in r.placements if p.exam_key in ("g1-0", "g2-0")]
    assert both[0] != both[1]


def test_group_never_has_two_exams_at_once():
    # Günde 2 synag rugsat, ýöne bir wagtda däl.
    exams = [exam(f"e{i}", [1], [i]) for i in range(4)]
    inp, r = solve(exams, max_per_day=2, slots=slots(days=2, periods=2))
    assert r.ok, r.issues
    assert len({p.slot_id for p in r.placements}) == 4


def test_rest_days_between_exams():
    exams = [exam(f"e{i}", [1], [i]) for i in range(3)]
    inp, r = solve(exams, rest_days=1)
    assert r.ok, r.issues
    day = {s.id: s.day for s in inp.slots}
    used = sorted(day[p.slot_id] for p in r.placements)
    assert all((b - a).days >= 2 for a, b in zip(used, used[1:]))


def test_too_many_exams_reported_before_solving():
    _, r = solve([exam(f"e{i}", [1], [i]) for i in range(4)], rest_days=1)  # 5 günde iň köp 3 synag
    assert not r.ok and r.status == "precheck_failed"


def test_rooms_respect_faculty():
    rooms = [Room(1, 30, 1, faculty_id=1), Room(2, 30, 1, faculty_id=2), Room(3, 30, 1)]
    exams = [exam(f"f2-{i}", [i], [i], faculties=[2]) for i in range(4)]
    inp, r = solve(exams, rooms=rooms, slots=slots(days=1, periods=2))
    assert r.ok, r.issues
    assert {p.room_id for p in r.placements} <= {2, 3}
    assert max(Counter((p.slot_id, p.room_id) for p in r.placements).values()) == 1


def test_exam_schedule_api(client):
    b = make_basics(client)
    gid, dep = b["group"]["id"], b["department"]["id"]
    t1 = post(client, "teachers", name="Uly", department_id=dep)
    t2 = post(client, "teachers", name="Kiçi", department_id=dep)
    rt = post(client, "room-types", name="Okuw otagy")
    bld = post(client, "buildings", name="V")
    post(client, "rooms", name="101", capacity=30, building_id=bld["id"], room_type_id=rt["id"],
         faculty_id=b["faculty"]["id"])
    session = post(client, "exam-sessions", name="Ara synag", kind="midterm",
                   starts_on="2026-11-02", ends_on="2026-11-08", rest_days=1)
    assert session["weekdays"] == [1, 2, 3, 4, 5, 6]
    for n, (a, z) in enumerate([("09:00", "10:20"), ("10:30", "11:50")], start=1):
        post(client, "exam-periods", session_id=session["id"], number=n, starts_at=a, ends_at=z)
    subjects = [post(client, "subjects", name=f"Ders {i}", department_id=dep) for i in range(3)]
    for s in subjects:
        post(client, "exams", session_id=session["id"], subject_id=s["id"], group_id=gid,
             examiner_id=t1["id"], assistant_id=t2["id"])

    bad = client.post("/api/v1/exams", json={"session_id": session["id"], "subject_id": subjects[0]["id"],
                                             "group_id": gid, "examiner_id": t1["id"], "assistant_id": t1["id"]})
    assert bad.status_code == 422

    check = client.get(f"/api/v1/exam-schedules/precheck?session_id={session['id']}").json()
    assert check == {"exams": 3, "days": 6, "slots": 12, "issues": []}

    r = client.post("/api/v1/exam-schedules", json={"session_id": session["id"], "name": "v1",
                                                     "time_limit_seconds": 10})
    assert r.status_code == 202, r.text
    sch = client.get(f"/api/v1/exam-schedules/{r.json()['id']}").json()
    assert sch["status"] == "done", sch["issues"]
    assert sch["entry_count"] == 3

    entries = client.get(f"/api/v1/exam-schedules/{sch['id']}/entries?teacher_id={t2['id']}").json()
    assert len(entries) == 3
    days = sorted(date.fromisoformat(e["day"]) for e in entries)
    assert all((b - a).days >= 2 for a, b in zip(days, days[1:]))
    assert all(e["room"]["name"] == "101" and e["assistant"]["name"] == "Kiçi" for e in entries)
    assert all(e["weekday"] != 7 for e in entries)
