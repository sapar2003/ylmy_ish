def post(client, path, **data):
    r = client.post(f"/api/v1/{path}", json=data)
    assert r.status_code == 201, r.text
    return r.json()


def make_basics(client):
    """Fakultet -> kafedra -> hünär -> smena -> topar (2 kiçi topar bilen)."""
    f = post(client, "faculties", name="Informatika")
    d = post(client, "departments", name="Programmirleme", faculty_id=f["id"])
    sp = post(client, "specialties", name="PÜ", level="bachelor", department_id=d["id"])
    sh = post(client, "shifts", name="Irden", starts_at="08:30", ends_at="13:20")
    g = post(client, "groups", name="PO-101", course=1, student_count=24, specialty_id=sp["id"], shift_id=sh["id"])
    subs = [post(client, "subgroups", name=n, student_count=12, group_id=g["id"]) for n in ("1", "2")]
    return {"faculty": f, "department": d, "specialty": sp, "shift": sh, "group": g, "subgroups": subs}
