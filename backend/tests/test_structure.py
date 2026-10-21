def make_faculty(client, name="Informatika"):
    r = client.post("/api/v1/faculties", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


def test_add_and_remove_any_number_of_faculties(client):
    ids = [make_faculty(client, f"Fakultet {i}")["id"] for i in range(25)]
    assert client.get("/api/v1/faculties?limit=500").json()["total"] == 25

    for fid in ids[:10]:
        assert client.delete(f"/api/v1/faculties/{fid}").status_code == 204
    assert client.get("/api/v1/faculties").json()["total"] == 15
    assert client.get(f"/api/v1/faculties/{ids[0]}").status_code == 404


def test_update_faculty(client):
    f = make_faculty(client)
    r = client.patch(f"/api/v1/faculties/{f['id']}", json={"short_name": "IT"})
    assert r.status_code == 200
    assert r.json()["short_name"] == "IT"
    assert r.json()["name"] == "Informatika"


def test_duplicate_faculty_name_conflicts(client):
    make_faculty(client)
    assert client.post("/api/v1/faculties", json={"name": "Informatika"}).status_code == 409


def test_cannot_delete_faculty_with_departments(client):
    f = make_faculty(client)
    d = client.post("/api/v1/departments", json={"name": "Programmirleme", "faculty_id": f["id"]}).json()
    assert client.delete(f"/api/v1/faculties/{f['id']}").status_code == 409
    assert client.delete(f"/api/v1/departments/{d['id']}").status_code == 204
    assert client.delete(f"/api/v1/faculties/{f['id']}").status_code == 204


def test_department_needs_existing_faculty(client):
    r = client.post("/api/v1/departments", json={"name": "X", "faculty_id": 999})
    assert r.status_code == 422


def test_full_hierarchy_and_filters(client):
    f1, f2 = make_faculty(client, "A"), make_faculty(client, "B")
    d1 = client.post("/api/v1/departments", json={"name": "K1", "faculty_id": f1["id"]}).json()
    client.post("/api/v1/departments", json={"name": "K2", "faculty_id": f2["id"]})
    listed = client.get(f"/api/v1/departments?faculty_id={f1['id']}").json()
    assert [d["name"] for d in listed["items"]] == ["K1"]

    sp = client.post(
        "/api/v1/specialties",
        json={"name": "Programma üpjünçiligi", "level": "master", "duration_years": 2, "department_id": d1["id"]},
    ).json()
    sh = client.post("/api/v1/shifts", json={"name": "Öýlän", "starts_at": "13:30", "ends_at": "18:40"}).json()
    g = client.post(
        "/api/v1/groups",
        json={"name": "M-101", "course": 1, "student_count": 24, "specialty_id": sp["id"], "shift_id": sh["id"]},
    )
    assert g.status_code == 201, g.text
    gid = g.json()["id"]
    for n in ("1", "2"):
        assert client.post("/api/v1/subgroups", json={"name": n, "student_count": 12, "group_id": gid}).status_code == 201

    # Topar aýrylanda kiçi toparlary hem aýrylýar.
    assert client.delete(f"/api/v1/groups/{gid}").status_code == 204
    assert client.get("/api/v1/subgroups").json()["total"] == 0


def test_shift_time_order_validated(client):
    r = client.post("/api/v1/shifts", json={"name": "Irden", "starts_at": "13:00", "ends_at": "08:00"})
    assert r.status_code == 422


def test_search_by_name(client):
    make_faculty(client, "Ykdysadyýet")
    make_faculty(client, "Informatika")
    items = client.get("/api/v1/faculties?q=inform").json()["items"]
    assert [f["name"] for f in items] == ["Informatika"]
