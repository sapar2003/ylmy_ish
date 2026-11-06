from datetime import date, timedelta

from app.services.journal import editable
from app import models as m
from tests.conftest import client_session_factory
from tests.test_users import login, setup


def _lesson_on(c, teacher, day):
    """Mugallymyň `day` güni bolýan sapaklary."""
    week = c.get(f"/api/v1/me/timetable?on={day.isoformat()}", headers=teacher).json()
    return [e for e in week["entries"] if e["weekday"] == day.isoweekday()]


def test_editable_window():
    teacher = m.User(role=m.Role.teacher)
    admin = m.User(role=m.Role.admin)
    d = date(2026, 10, 5)
    assert editable(teacher, d, today=d) and editable(teacher, d, today=d + timedelta(days=3))
    assert not editable(teacher, d, today=d + timedelta(days=4))
    assert not editable(teacher, d, today=d - timedelta(days=1))  # sapak heniz bolmady
    assert editable(admin, d, today=d + timedelta(days=30))


def test_teacher_marks_students(anon_client):
    c = anon_client
    admin = setup(c)
    assert c.post("/api/v1/students/demo", headers=admin).json()["created"] > 0
    assert c.post("/api/v1/students/demo", headers=admin).json()["created"] == 0  # ikinji gezek döredilmeýär
    studs = c.get("/api/v1/students?limit=500", headers=admin).json()
    assert studs["total"] > 0

    issued = c.post("/api/v1/users/teachers", json={}, headers=admin).json()
    acc = next(i for i in issued if i["teacher"]["name"] == "A. Annaýew")
    teacher, _ = login(c, acc["username"], acc["password"])
    assert c.get("/api/v1/students", headers=teacher).status_code == 403

    today = date.today()
    tt = c.post("/api/v1/timetables", json={"name": "Güýz", "time_limit_seconds": 20, "weeks": 2,
                                           "starts_on": (today - timedelta(days=60)).isoformat()}, headers=admin).json()
    c.post(f"/api/v1/timetables/{tt['id']}/publish", json={"published": True}, headers=admin)

    # Soňky 3 günüň içinde bolan sapak we 3 günden öň bolan sapak.
    recent = next((d, e) for k in range(4) if (d := today - timedelta(days=k)) for e in _lesson_on(c, teacher, d))
    old = next((d, e) for k in range(5, 30) if (d := today - timedelta(days=k)) for e in _lesson_on(c, teacher, d))

    day, entry = recent
    assert entry["assignment_id"]
    les = c.get(f"/api/v1/me/lesson?entry_id={entry['id']}&day={day}", headers=teacher).json()
    assert les["editable"] and les["students"] and all(s["mark"] is None for s in les["students"])
    s1, s2 = les["students"][0]["id"], les["students"][1]["id"]

    r = c.put("/api/v1/me/lesson", json={"entry_id": entry["id"], "day": day.isoformat(),
                                         "marks": [{"student_id": s1, "value": "5"}, {"student_id": s2, "value": "gm"}]},
              headers=teacher)
    assert r.status_code == 200, r.text
    marks = {s["id"]: s["mark"] for s in r.json()["students"]}
    assert marks[s1] == "5" and marks[s2] == "gm"
    assert c.put("/api/v1/me/lesson", json={"entry_id": entry["id"], "day": day.isoformat(),
                                            "marks": [{"student_id": s1, "value": "6"}]}, headers=teacher).status_code == 422
    # Düzetmek we aýyrmak.
    c.put("/api/v1/me/lesson", json={"entry_id": entry["id"], "day": day.isoformat(),
                                     "marks": [{"student_id": s1, "value": "4"}, {"student_id": s2, "value": None}]},
          headers=teacher)
    with client_session_factory[0]() as db:
        assert db.query(m.MarkLog).count() == 4

    # Nädogry gün (hepde güni gabat gelmeýär).
    wrong = day + timedelta(days=1)
    assert c.get(f"/api/v1/me/lesson?entry_id={entry['id']}&day={wrong}", headers=teacher).status_code == 422

    # 3 günden köp geçen sapaga mugallym baha goýup bilmeýär, admin bolsa bilýär.
    oday, oentry = old
    les_old = c.get(f"/api/v1/me/lesson?entry_id={oentry['id']}&day={oday}", headers=teacher).json()
    assert not les_old["editable"]
    sid = les_old["students"][0]["id"]
    assert c.put("/api/v1/me/lesson", json={"entry_id": oentry["id"], "day": oday.isoformat(),
                                            "marks": [{"student_id": sid, "value": "3"}]},
                 headers=teacher).status_code == 403
    r = c.put(f"/api/v1/journal/{oentry['assignment_id']}", json={
        "student_id": sid, "day": oday.isoformat(), "time_slot_id": oentry["time_slot_id"], "value": "3"},
              headers=admin)
    assert r.status_code == 200, r.text

    # Başga mugallymyň sapagy.
    other = next(i for i in issued if i["teacher"]["name"] != "A. Annaýew")
    other_h, _ = login(c, other["username"], other["password"])
    assert c.get(f"/api/v1/me/lesson?entry_id={entry['id']}&day={day}", headers=other_h).status_code == 403

    # Žurnal: mugallym we admin.
    courses = c.get("/api/v1/me/courses", headers=teacher).json()
    assert any(x["assignment_id"] == entry["assignment_id"] for x in courses)
    book = c.get(f"/api/v1/me/journal/{entry['assignment_id']}", headers=teacher).json()
    col = next(i for i, x in enumerate(book["columns"]) if x["day"] == day.isoformat())
    row = next(r for r in book["rows"] if r["student"]["id"] == s1)
    assert row["marks"][col] == "4" and row["average"] is not None
    assert c.get(f"/api/v1/me/journal/{entry['assignment_id']}", headers=other_h).status_code == 403

    group_id = c.get("/api/v1/groups?limit=500", headers=admin).json()["items"][0]["id"]
    assert isinstance(c.get(f"/api/v1/journal/courses?group_id={group_id}", headers=admin).json(), list)
    assert c.get(f"/api/v1/journal/{entry['assignment_id']}", headers=admin).json()["rows"]


def test_student_sees_only_own_marks(anon_client):
    c = anon_client
    admin = setup(c)
    assert c.post("/api/v1/students/demo", headers=admin).json()["created"] > 0
    today = date.today()
    tt = c.post("/api/v1/timetables", json={"name": "Güýz", "time_limit_seconds": 20, "weeks": 2,
                                           "starts_on": (today - timedelta(days=60)).isoformat()}, headers=admin).json()
    c.post(f"/api/v1/timetables/{tt['id']}/publish", json={"published": True}, headers=admin)
    entries = c.get(f"/api/v1/timetables/{tt['id']}/entries", headers=admin).json()
    # Geçen günleriň biri: şol günde bolýan sapak.
    day, entry = next((d, e) for k in range(14) if (d := today - timedelta(days=k + 5))
                      for e in c.get(f"/api/v1/timetables/{tt['id']}/entries?on={d}", headers=admin).json()
                      if e["weekday"] == d.isoweekday())
    assert entries
    r = c.get(f"/api/v1/students?group_id={entry['groups'][0]['id']}&limit=500", headers=admin).json()["items"]
    mine = next(s for s in r if entry["subgroup"] is None or s["subgroup_id"] == entry["subgroup"]["id"])
    other = next(s for s in r if s["id"] != mine["id"] and (entry["subgroup"] is None or s["subgroup_id"] == entry["subgroup"]["id"]))
    for s, value in ((mine, "5"), (other, "2")):
        assert c.put(f"/api/v1/journal/{entry['assignment_id']}", json={
            "student_id": s["id"], "day": day.isoformat(), "time_slot_id": entry["time_slot_id"], "value": value},
            headers=admin).status_code == 200

    assert c.patch(f"/api/v1/students/{mine['id']}", json={"phone": "65222222"}, headers=admin).status_code == 200
    with client_session_factory[0]() as db:
        from app.services.accounts import user_by_phone
        user = user_by_phone(db, "+99365222222")
        uid = user.id
    from app.core.security import create_token
    h = {"Authorization": f"Bearer {create_token(uid)}"}
    assert c.get("/api/v1/me/marks").status_code == 401
    assert c.get("/api/v1/me/marks", headers=admin).status_code == 403  # diňe talyp
    data = c.get("/api/v1/me/marks", headers=h).json()
    course = next(x for x in data if x["assignment_id"] == entry["assignment_id"])
    assert [m["value"] for m in course["marks"]] == ["5"] and course["average"] == 5  # başga talybyň 2-si ýok
    assert course["marks"][0]["day"] == day.isoformat() and course["marks"][0]["can_change"] is False
    assert course["teacher"] and course["absent"] == 0
    # Beýleki sahypalar ýapyk: talyp žurnaly we başga talyplary görüp bilmeýär.
    assert c.get(f"/api/v1/journal/{entry['assignment_id']}", headers=h).status_code == 403
    assert c.get("/api/v1/students", headers=h).status_code == 403
