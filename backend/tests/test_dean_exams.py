"""Dekanlar diňe öz fakultetiniň synag möwsümlerini we raspisaniýelerini görýär (serwer tarapynda)."""
from tests.test_dean import _dean, _ids


def _session_with_exam(c, admin, name, group_id, teacher_id, subject_id):
    sess = c.post("/api/v1/exam-sessions", json={"name": name, "kind": "final", "starts_on": "2027-01-12",
                                                 "ends_on": "2027-01-20", "consultations": True}, headers=admin)
    assert sess.status_code == 201, sess.text
    sid = sess.json()["id"]
    c.post("/api/v1/exam-periods", json={"session_id": sid, "number": 1, "starts_at": "08:30",
                                         "ends_at": "09:50"}, headers=admin)
    r = c.post("/api/v1/exams", json={"session_id": sid, "group_id": group_id, "subject_id": subject_id,
                                      "examiner_id": teacher_id}, headers=admin)
    assert r.status_code == 201, r.text
    sch = c.post("/api/v1/exam-schedules", json={"session_id": sid, "name": f"{name} tertip",
                                                 "time_limit_seconds": 5}, headers=admin)
    assert sch.status_code == 202, sch.text
    return sid, sch.json()["id"]


def test_deans_see_only_own_exam_sessions_and_schedules(anon_client):
    c = anon_client
    from tests.test_users import setup
    admin = setup(c)
    dean_a, fac_a = _dean(c, admin, "IHT")
    dean_b, fac_b = _dean(c, admin, "YK")
    group_a = next(iter(_ids(c, "groups", dean_a)))
    group_b = next(iter(_ids(c, "groups", dean_b)))
    teacher = next(iter(_ids(c, "teachers", admin)))
    subject = next(iter(_ids(c, "subjects", admin)))
    sess_a, sch_a = _session_with_exam(c, admin, "Synag A", group_a, teacher, subject)
    sess_b, sch_b = _session_with_exam(c, admin, "Synag B", group_b, teacher, subject)

    # Admin hemmesini görýär
    assert {sess_a, sess_b} <= _ids(c, "exam-sessions", admin)
    assert {sch_a, sch_b} <= {s["id"] for s in c.get("/api/v1/exam-schedules", headers=admin).json()}

    for dean, own_sess, own_sch, other_sess, other_sch in (
            (dean_a, sess_a, sch_a, sess_b, sch_b), (dean_b, sess_b, sch_b, sess_a, sch_a)):
        assert _ids(c, "exam-sessions", dean) == {own_sess}
        periods = c.get("/api/v1/exam-periods?limit=500", headers=dean).json()["items"]
        assert {p["session_id"] for p in periods} == {own_sess}
        assert {s["id"] for s in c.get("/api/v1/exam-schedules", headers=dean).json()} == {own_sch}
        assert c.get(f"/api/v1/exam-schedules/{own_sch}", headers=dean).status_code == 200
        # Başga fakultetiňki: 404
        assert c.get(f"/api/v1/exam-sessions/{other_sess}", headers=dean).status_code == 404
        assert c.get(f"/api/v1/exam-schedules/{other_sch}", headers=dean).status_code == 404
        assert c.get(f"/api/v1/exam-schedules/{other_sch}/entries", headers=dean).status_code == 404
        assert c.get(f"/api/v1/exam-schedules/{other_sch}/docx?page={group_a},{group_b}",
                     headers=dean).status_code in (403, 404)
        # Üýtgetmek, düzmek, pozmak, çap etmek: diňe okuw bölümi (admin)
        assert c.patch(f"/api/v1/exam-sessions/{own_sess}", json={"name": "X"}, headers=dean).status_code in (403, 404)
        assert c.post("/api/v1/exam-schedules", json={"session_id": own_sess, "name": "X"},
                      headers=dean).status_code == 403
        assert c.delete(f"/api/v1/exam-schedules/{own_sch}", headers=dean).status_code == 403
        assert c.post(f"/api/v1/exam-schedules/{own_sch}/publish", json={"published": True},
                      headers=dean).status_code == 403
        # Synaglar: diňe öz toparlarynyňky
        exams = c.get("/api/v1/exams?limit=500", headers=dean).json()["items"]
        assert {e["session_id"] for e in exams} == {own_sess}


def test_archive_rename_and_publish_rules(anon_client):
    c = anon_client
    from tests.test_users import setup
    admin = setup(c)
    dean, _ = _dean(c, admin, "IHT")
    group = next(iter(_ids(c, "groups", dean)))
    teacher = next(iter(_ids(c, "teachers", admin)))
    subject = next(iter(_ids(c, "subjects", admin)))
    _, sch = _session_with_exam(c, admin, "Synag C", group, teacher, subject)
    url = f"/api/v1/exam-schedules/{sch}"
    assert c.patch(url, json={"archived": True}, headers=dean).status_code == 403
    r = c.patch(url, json={"archived": True, "name": "Köne"}, headers=admin)
    assert r.status_code == 200 and r.json()["archived"] and r.json()["name"] == "Köne"
    if c.get(url, headers=admin).json()["status"] == "done":
        assert c.post(f"{url}/publish", json={"published": True}, headers=admin).status_code == 200
        assert c.get(url, headers=admin).json()["archived"] is False  # çap edilen yzyna gelýär
        assert c.patch(url, json={"archived": True}, headers=admin).status_code == 409
