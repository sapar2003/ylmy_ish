from datetime import date, timedelta

from app.core.config import settings
from tests.test_users import login, setup


def test_teacher_sets_topic_and_file_students_see_it(anon_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    c = anon_client
    admin = setup(c)
    issued = c.post("/api/v1/users/teachers", json={}, headers=admin).json()
    acc = next(i for i in issued if i["teacher"]["name"] == "A. Annaýew")
    teacher, _ = login(c, acc["username"], acc["password"])
    tt = c.post("/api/v1/timetables", json={"name": "Güýz", "time_limit_seconds": 20, "weeks": 2,
                                           "starts_on": "2026-09-01"}, headers=admin).json()
    c.post(f"/api/v1/timetables/{tt['id']}/publish", json={"published": True}, headers=admin)

    week = c.get("/api/v1/me/timetable?on=2026-09-09", headers=teacher).json()
    entry = week["entries"][0]
    day = date.fromisoformat(week["week_start"]) + timedelta(days=entry["weekday"] - 1)
    assert week["topics"] == []
    assert c.get(f"/api/v1/me/topic?entry_id={entry['id']}&day={day}", headers=teacher).json() is None

    r = c.put("/api/v1/me/topic", json={"entry_id": entry["id"], "day": day.isoformat(), "topic": "Sanawlar we massiwler"},
              headers=teacher)
    assert r.status_code == 200 and r.json()["topic"] == "Sanawlar we massiwler"
    r = c.put(f"/api/v1/me/topic/file?entry_id={entry['id']}&day={day}&name=tema-1.pptx", content=b"PPTX-DATA",
              headers=teacher)
    assert r.status_code == 200, r.text
    url = r.json()["file_url"]
    assert r.json()["file_name"] == "tema-1.pptx" and url
    assert c.put(f"/api/v1/me/topic/file?entry_id={entry['id']}&day={day}&name=x.exe", content=b"x",
                 headers=teacher).status_code == 422
    # Başga mugallym bu sapaga tema goýup bilmeýär.
    other = next(i for i in issued if i["teacher"]["name"] != "A. Annaýew")
    other_h, _ = login(c, other["username"], other["password"])
    assert c.put("/api/v1/me/topic", json={"entry_id": entry["id"], "day": day.isoformat(), "topic": "x"},
                 headers=other_h).status_code == 403

    # Mugallym we şol sapagy okaýan talyplar (girişsiz) temany we faýly görýär.
    assert c.get("/api/v1/me/timetable?on=2026-09-09", headers=teacher).json()["topics"][0]["topic"] == "Sanawlar we massiwler"
    group = entry["groups"][0]["id"]
    pub = c.get(f"/api/v1/public/timetable?group_id={group}&on={day}").json()
    topic = next(t for t in pub["topics"] if t["assignment_id"] == entry["assignment_id"])
    assert topic["file_url"] == url
    assert c.get(url).content == b"PPTX-DATA"

    # Faýly aýyrmak; tema galýar. Temany hem boşatsa ýazgy aýrylýar.
    assert c.delete(f"/api/v1/me/topic/file?entry_id={entry['id']}&day={day}", headers=teacher).json()["file_url"] is None
    assert c.get(url).status_code == 404
    assert c.put("/api/v1/me/topic", json={"entry_id": entry["id"], "day": day.isoformat(), "topic": ""},
                 headers=teacher).json() is None
