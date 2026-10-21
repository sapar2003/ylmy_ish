from tests.factories import make_basics, post


def setup(client):
    b = make_basics(client)
    b["subject"] = post(client, "subjects", name="Matematika", department_id=b["department"]["id"])
    b["t1"] = post(client, "teachers", name="A. Annaýew", department_id=b["department"]["id"])
    b["t2"] = post(client, "teachers", name="B. Berdiýew", department_id=b["department"]["id"])
    return b


def test_split_lesson_gets_teacher_per_subgroup(client):
    b = setup(client)
    item = post(
        client, "curriculum", subject_id=b["subject"]["id"], lesson_type="lab",
        lessons_per_week=2, group_id=b["group"]["id"], split=True,
    )
    s1, s2 = b["subgroups"]
    post(client, "assignments", curriculum_item_id=item["id"], teacher_id=b["t1"]["id"], subgroup_id=s1["id"])
    post(client, "assignments", curriculum_item_id=item["id"], teacher_id=b["t2"]["id"], subgroup_id=s2["id"])

    # Kiçi topar görkezilmese ýa-da gaýtalansa ret edilýär.
    r = client.post("/api/v1/assignments", json={"curriculum_item_id": item["id"], "teacher_id": b["t1"]["id"]})
    assert r.status_code == 422
    r = client.post(
        "/api/v1/assignments",
        json={"curriculum_item_id": item["id"], "teacher_id": b["t1"]["id"], "subgroup_id": s1["id"]},
    )
    assert r.status_code == 409

    listed = client.get(f"/api/v1/assignments?curriculum_item_id={item['id']}").json()
    assert listed["total"] == 2


def test_regular_lesson_has_one_teacher(client):
    b = setup(client)
    item = post(
        client, "curriculum", subject_id=b["subject"]["id"], lesson_type="practice",
        lessons_per_week=2, group_id=b["group"]["id"],
    )
    post(client, "assignments", curriculum_item_id=item["id"], teacher_id=b["t1"]["id"])
    r = client.post("/api/v1/assignments", json={"curriculum_item_id": item["id"], "teacher_id": b["t2"]["id"]})
    assert r.status_code == 409
    r = client.post(
        "/api/v1/assignments",
        json={"curriculum_item_id": item["id"], "teacher_id": b["t2"]["id"], "subgroup_id": b["subgroups"][0]["id"]},
    )
    assert r.status_code == 422


def test_stream_lecture(client):
    b = setup(client)
    g2 = post(
        client, "groups", name="PO-102", course=1, specialty_id=b["specialty"]["id"], shift_id=b["shift"]["id"]
    )
    stream = post(client, "streams", name="PÜ 1-nji ýyl", group_ids=[b["group"]["id"], g2["id"]])
    assert sorted(stream["group_ids"]) == sorted([b["group"]["id"], g2["id"]])

    item = post(
        client, "curriculum", subject_id=b["subject"]["id"], lesson_type="lecture",
        lessons_per_week=1, stream_id=stream["id"],
    )
    assert item["group_id"] is None

    # Potok sapagy bölünip bilmeýär; topar we potok bilelikde görkezilip bilmeýär.
    r = client.patch(f"/api/v1/curriculum/{item['id']}", json={"split": True})
    assert r.status_code == 422
    r = client.post(
        "/api/v1/curriculum",
        json={"subject_id": b["subject"]["id"], "lesson_type": "lecture", "lessons_per_week": 1,
              "group_id": b["group"]["id"], "stream_id": stream["id"]},
    )
    assert r.status_code == 422

    r = client.patch(f"/api/v1/streams/{stream['id']}", json={"group_ids": [b["group"]["id"], 999]})
    assert r.status_code == 422


def test_split_requires_subgroups(client):
    b = setup(client)
    g2 = post(client, "groups", name="PO-103", course=1, specialty_id=b["specialty"]["id"])
    r = client.post(
        "/api/v1/curriculum",
        json={"subject_id": b["subject"]["id"], "lesson_type": "lab", "lessons_per_week": 1,
              "group_id": g2["id"], "split": True},
    )
    assert r.status_code == 422


def test_deleting_curriculum_item_removes_assignments(client):
    b = setup(client)
    item = post(
        client, "curriculum", subject_id=b["subject"]["id"], lesson_type="practice",
        lessons_per_week=2, group_id=b["group"]["id"],
    )
    post(client, "assignments", curriculum_item_id=item["id"], teacher_id=b["t1"]["id"])
    assert client.delete(f"/api/v1/curriculum/{item['id']}").status_code == 204
    assert client.get("/api/v1/assignments").json()["total"] == 0
    # Mugallymy indi aýryp bolýar.
    assert client.delete(f"/api/v1/teachers/{b['t1']['id']}").status_code == 204
