from tests.test_users import setup


def test_student_sees_group_timetable_without_login(anon_client):
    c = anon_client
    admin = setup(c)
    groups = c.get("/api/v1/public/groups").json()
    assert groups and all("faculty" in g and "subgroups" in g for g in groups)
    group = next(g for g in groups if g["subgroups"]) if any(g["subgroups"] for g in groups) else groups[0]
    # Çap edilmedik raspisaniýe görünmeýär.
    assert c.get(f"/api/v1/public/timetable?group_id={group['id']}").json()["timetable"] is None

    tt = c.post("/api/v1/timetables", json={"name": "Güýz", "time_limit_seconds": 20, "weeks": 2,
                                           "starts_on": "2026-09-01"}, headers=admin).json()
    c.post(f"/api/v1/timetables/{tt['id']}/publish", json={"published": True}, headers=admin)
    week = c.get(f"/api/v1/public/timetable?group_id={group['id']}&on=2026-09-02").json()
    assert week["timetable"]["id"] == tt["id"] and week["week"] == 1 and week["entries"]
    e = week["entries"][0]
    assert e["teacher"]["name"] and e["subject"]["name"] and e["starts_at"]
    assert all(group["id"] in {g["id"] for g in x["groups"]} for x in week["entries"])
    if group["subgroups"]:
        sg = group["subgroups"][0]["id"]
        mine = c.get(f"/api/v1/public/timetable?group_id={group['id']}&subgroup_id={sg}&on=2026-09-02").json()
        assert all(x["subgroup"] is None or x["subgroup"]["id"] == sg for x in mine["entries"])
        assert len(mine["entries"]) <= len(week["entries"])
    assert c.get(f"/api/v1/public/exams?group_id={group['id']}").json() == []
    assert c.get("/api/v1/public/timetable?group_id=99999").status_code == 404
