from collections import Counter

from app.seed import seed
from tests.conftest import client_session_factory


def seeded(client):
    with client_session_factory[0]() as db:
        seed(db)
    return client


def test_precheck_on_demo_data(client):
    r = seeded(client).get("/api/v1/timetables/precheck")
    assert r.status_code == 200
    body = r.json()
    assert body["lessons"] > 20
    assert body["issues"] == []


def test_generate_demo_timetable_without_conflicts(client):
    seeded(client)
    r = client.post("/api/v1/timetables", json={"name": "Güýz 2026", "time_limit_seconds": 20})
    assert r.status_code == 202, r.text
    tt = client.get(f"/api/v1/timetables/{r.json()['id']}").json()
    assert tt["status"] == "done", tt["issues"]
    assert tt["entry_count"] > 0

    entries = client.get(f"/api/v1/timetables/{tt['id']}/entries").json()
    # Mugallym we otag bir wagtda diňe bir ýerde.
    assert max(Counter((e["teacher"]["id"], e["time_slot_id"]) for e in entries).values()) == 1
    assert max(Counter((e["room"]["id"], e["time_slot_id"]) for e in entries).values()) == 1
    assert all(e["room"] is not None for e in entries)

    # Topar: umumy sapak kiçi topar sapagy bilen gabat gelmeýär.
    groups = {g["id"] for e in entries for g in e["groups"]}
    for gid in groups:
        mine = client.get(f"/api/v1/timetables/{tt['id']}/entries?group_id={gid}").json()
        by_slot = {}
        for e in mine:
            by_slot.setdefault(e["time_slot_id"], []).append(e)
        for same in by_slot.values():
            if len(same) > 1:
                assert all(e["subgroup"] is not None for e in same)
                assert len({e["subgroup"]["id"] for e in same}) == len(same)

    # Annaýew iki fakultetde okadýar we duşenbe irden sapagy ýok.
    annayev = [e for e in entries if e["teacher"]["name"] == "A. Annaýew"]
    faculties_groups = {g["name"][:2] for e in annayev for g in e["groups"]}
    assert {"PÜ", "ML"} <= faculties_groups
    assert not [e for e in annayev if e["weekday"] == 1 and e["starts_at"] < "13:00"]


def test_generation_fails_cleanly_without_data(client):
    r = client.post("/api/v1/timetables", json={"name": "Boş"})
    tt = client.get(f"/api/v1/timetables/{r.json()['id']}").json()
    assert tt["status"] == "failed"
    assert tt["issues"]
    assert client.delete(f"/api/v1/timetables/{tt['id']}").status_code == 204


def test_iogu_dataset_generates_without_conflicts(client):
    from app.seed_iogu import seed_iogu

    with client_session_factory[0]() as db:
        seed_iogu(db)
    faculties = client.get("/api/v1/faculties").json()["items"]
    assert len(faculties) == 8
    assert client.get("/api/v1/timetables/precheck").json()["issues"] == []

    r = client.post("/api/v1/timetables", json={"name": "HNGU", "time_limit_seconds": 60})
    tt = client.get(f"/api/v1/timetables/{r.json()['id']}").json()
    assert tt["status"] == "done", tt["issues"]
    entries = client.get(f"/api/v1/timetables/{tt['id']}/entries").json()
    assert max(Counter((e["teacher"]["id"], e["time_slot_id"]) for e in entries).values()) == 1
    assert max(Counter((e["room"]["id"], e["time_slot_id"]) for e in entries).values()) == 1
