from tests.test_users import login, setup


def _dean(c, admin, faculty_name):
    fac = next(f for f in c.get("/api/v1/faculties", headers=admin).json()["items"] if f["short_name"] == faculty_name)
    issued = c.post("/api/v1/users/deans", json={"faculty_id": fac["id"]}, headers=admin).json()
    assert issued["username"] == f"dekan.{faculty_name.lower()}" and issued["faculty"]["id"] == fac["id"]
    headers, me = login(c, issued["username"], issued["password"])
    assert me["role"] == "dean" and me["faculty"]["id"] == fac["id"]
    return headers, fac


def _ids(c, path, headers):
    return {x["id"] for x in c.get(f"/api/v1/{path}?limit=500", headers=headers).json()["items"]}


def test_dean_sees_and_edits_only_own_faculty(anon_client):
    c = anon_client
    admin = setup(c)
    dean, fac = _dean(c, admin, "IHT")
    other_dean, _ = _dean(c, admin, "YK")

    # Görmek: diňe öz fakultetiniň hünärleri, toparlary, meýilnamasy (kafedralar hemmesi görünýär).
    own_deps = {d["id"] for d in c.get("/api/v1/departments?limit=500", headers=admin).json()["items"]
                if d["faculty_id"] == fac["id"]}
    assert {s["department_id"] for s in c.get("/api/v1/specialties", headers=dean).json()["items"]} <= own_deps
    foreign_dep = next(iter(_ids(c, "departments", dean) - own_deps))
    assert c.patch(f"/api/v1/departments/{foreign_dep}", json={"name": "X"}, headers=dean).status_code == 403
    all_groups, own_groups = _ids(c, "groups", admin), _ids(c, "groups", dean)
    assert own_groups and own_groups < all_groups
    assert own_groups.isdisjoint(_ids(c, "groups", other_dean))
    own_items = c.get("/api/v1/curriculum?limit=500", headers=dean).json()["items"]
    assert own_items and len(own_items) < c.get("/api/v1/curriculum?limit=500", headers=admin).json()["total"]
    # Mugallymlar we dersler: hemmesi görünýär (başga fakultetiň mugallymyny saýlamak üçin).
    assert _ids(c, "teachers", dean) == _ids(c, "teachers", admin)

    # Başga fakultetiň toparyny görmek we üýtgetmek bolmaýar.
    foreign_group = next(iter(all_groups - own_groups))
    assert c.get(f"/api/v1/groups/{foreign_group}", headers=dean).status_code == 404
    assert c.patch(f"/api/v1/groups/{foreign_group}", json={"student_count": 1}, headers=dean).status_code == 404

    # Öz toparyny üýtgedip bilýär, başga fakultete geçirip bilmeýär.
    group_id = next(iter(own_groups))
    assert c.patch(f"/api/v1/groups/{group_id}", json={"student_count": 21}, headers=dean).status_code == 200
    foreign_spec = next(s for s in c.get("/api/v1/specialties?limit=500", headers=admin).json()["items"]
                        if s["department_id"] not in own_deps)
    r = c.patch(f"/api/v1/groups/{group_id}", json={"specialty_id": foreign_spec["id"]}, headers=dean)
    assert r.status_code == 403
    assert c.post("/api/v1/groups", json={"name": "X-1", "course": 1, "specialty_id": foreign_spec["id"]},
                  headers=dean).status_code == 403

    # Başga fakultetiň mugallymy: görýär, üýtgedip bilmeýär, ýöne öz sapagyna belläp bilýär.
    teachers = c.get("/api/v1/teachers?limit=500", headers=admin).json()["items"]
    foreign_teacher = next(t for t in teachers if t["department_id"] not in own_deps)
    assert c.patch(f"/api/v1/teachers/{foreign_teacher['id']}", json={"position": "x"},
                   headers=dean).status_code == 403
    assert c.put(f"/api/v1/teachers/{foreign_teacher['id']}/availability", json=[], headers=dean).status_code == 403
    item = next(i for i in own_items if not i["split"])
    existing = c.get(f"/api/v1/assignments?curriculum_item_id={item['id']}", headers=dean).json()["items"]
    if existing:
        r = c.patch(f"/api/v1/assignments/{existing[0]['id']}", json={"teacher_id": foreign_teacher["id"]}, headers=dean)
    else:
        r = c.post("/api/v1/assignments", json={"curriculum_item_id": item["id"], "teacher_id": foreign_teacher["id"]},
                   headers=dean)
    assert r.status_code in (200, 201), r.text

    # Umumy sanawlar we raspisaniýe düzmek — diňe admin.
    assert c.get("/api/v1/shifts", headers=dean).status_code == 200
    assert c.post("/api/v1/buildings", json={"name": "B-9"}, headers=dean).status_code == 403
    assert c.post("/api/v1/timetables", json={"name": "x", "time_limit_seconds": 5}, headers=dean).status_code == 403
    assert c.get("/api/v1/users", headers=dean).status_code == 403

    # Raspisaniýe: dekan diňe öz toparlarynyň sapaklaryny görýär.
    tt = c.post("/api/v1/timetables", json={"name": "Güýz", "time_limit_seconds": 20}, headers=admin).json()
    entries = c.get(f"/api/v1/timetables/{tt['id']}/entries", headers=dean).json()
    assert entries and all(own_groups & {g["id"] for g in e["groups"]} for e in entries)
    assert len(entries) < len(c.get(f"/api/v1/timetables/{tt['id']}/entries", headers=admin).json())
    assert c.get(f"/api/v1/timetables/{tt['id']}/docx?page={foreign_group}", headers=dean).status_code == 403

    # Mugallym hasaby dekan sahypalaryna girip bilmeýär.
    issued = c.post("/api/v1/users/teachers", json={}, headers=admin).json()
    teacher, _ = login(c, issued[0]["username"], issued[0]["password"])
    assert c.get("/api/v1/groups", headers=teacher).status_code == 403
