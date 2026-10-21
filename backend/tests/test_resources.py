from tests.factories import make_basics, post

PERIODS = [
    {"number": 1, "starts_at": "08:30", "ends_at": "09:50"},
    {"number": 2, "starts_at": "10:00", "ends_at": "11:20"},
    {"number": 3, "starts_at": "11:50", "ends_at": "13:10"},
]


def test_generate_time_slots_for_shift(client):
    b = make_basics(client)
    r = client.post(
        "/api/v1/time-slots/generate",
        json={"shift_id": b["shift"]["id"], "weekdays": [1, 2, 3, 4, 5, 6], "periods": PERIODS},
    )
    assert r.status_code == 201, r.text
    assert len(r.json()) == 18
    monday = client.get(f"/api/v1/time-slots?shift_id={b['shift']['id']}&weekday=1").json()
    assert [s["number"] for s in monday["items"]] == [1, 2, 3]

    # Gaýtadan döretmek gaýtalanýan slot döretmeýär.
    again = client.post("/api/v1/time-slots/generate", json={"shift_id": b["shift"]["id"], "periods": PERIODS})
    assert again.status_code == 409


def test_teacher_availability_replace(client):
    b = make_basics(client)
    slots = client.post(
        "/api/v1/time-slots/generate", json={"shift_id": b["shift"]["id"], "weekdays": [1], "periods": PERIODS}
    ).json()
    t = post(client, "teachers", name="A. Annaýew", department_id=b["department"]["id"], max_lessons_per_day=4)

    body = [
        {"time_slot_id": slots[0]["id"], "status": "unavailable"},
        {"time_slot_id": slots[1]["id"], "status": "preferred"},
    ]
    r = client.put(f"/api/v1/teachers/{t['id']}/availability", json=body)
    assert r.status_code == 200, r.text
    assert client.get(f"/api/v1/teachers/{t['id']}/availability").json() == body

    r = client.put(f"/api/v1/teachers/{t['id']}/availability", json=body[:1])
    assert client.get(f"/api/v1/teachers/{t['id']}/availability").json() == body[:1]

    bad = client.put(f"/api/v1/teachers/{t['id']}/availability", json=[{"time_slot_id": 999, "status": "preferred"}])
    assert bad.status_code == 422


def test_teacher_from_other_faculty_lists_under_own_department(client):
    b = make_basics(client)
    f2 = post(client, "faculties", name="Ykdysadyýet")
    d2 = post(client, "departments", name="Matematika", faculty_id=f2["id"])
    post(client, "teachers", name="B. Berdiýew", department_id=d2["id"])
    post(client, "teachers", name="A. Annaýew", department_id=b["department"]["id"])
    names = [t["name"] for t in client.get(f"/api/v1/teachers?department_id={d2['id']}").json()["items"]]
    assert names == ["B. Berdiýew"]


def test_rooms(client):
    bld = post(client, "buildings", name="Esasy bina")
    lab = post(client, "room-types", name="Kompýuter otagy")
    post(client, "rooms", name="301", capacity=30, building_id=bld["id"], room_type_id=lab["id"])
    assert client.post(
        "/api/v1/rooms", json={"name": "301", "capacity": 20, "building_id": bld["id"], "room_type_id": lab["id"]}
    ).status_code == 409
    assert client.post(
        "/api/v1/rooms", json={"name": "302", "capacity": 0, "building_id": bld["id"], "room_type_id": lab["id"]}
    ).status_code == 422
    assert client.delete(f"/api/v1/room-types/{lab['id']}").status_code == 409
