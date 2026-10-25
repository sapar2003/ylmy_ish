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
    assert len(faculties) == 7
    assert client.get("/api/v1/timetables/precheck").json()["issues"] == []

    r = client.post("/api/v1/timetables", json={"name": "HNGU", "time_limit_seconds": 60})
    tt = client.get(f"/api/v1/timetables/{r.json()['id']}").json()
    assert tt["status"] == "done", tt["issues"]
    entries = client.get(f"/api/v1/timetables/{tt['id']}/entries").json()
    assert max(Counter((e["teacher"]["id"], e["time_slot_id"]) for e in entries).values()) == 1
    assert max(Counter((e["room"]["id"], e["time_slot_id"]) for e in entries).values()) == 1


def test_two_week_timetable_with_semester_dates(client):
    seeded(client)
    items = client.get("/api/v1/curriculum?limit=500").json()["items"]
    item = next(i for i in items if i["lessons_per_week"] >= 2 and not i["split"] and i["group_id"])
    r = client.patch(f"/api/v1/curriculum/{item['id']}",
                     json={"lessons_per_week": item["lessons_per_week"] - 1, "biweekly": 1})
    assert r.status_code == 200 and r.json()["biweekly"] == 1
    assert client.patch(f"/api/v1/curriculum/{item['id']}",
                        json={"lessons_per_week": 0, "biweekly": 0}).status_code == 422

    assert client.get("/api/v1/timetables/precheck?weeks=2").json()["issues"] == []
    r = client.post("/api/v1/timetables", json={"name": "Iki hepde", "time_limit_seconds": 20, "weeks": 2,
                                                "starts_on": "2026-09-01", "ends_on": "2026-12-31"})
    tt = client.get(f"/api/v1/timetables/{r.json()['id']}").json()
    assert tt["status"] == "done", tt["issues"]
    assert (tt["weeks"], tt["starts_on"]) == (2, "2026-09-01")

    url = f"/api/v1/timetables/{tt['id']}/entries"
    biweekly = [e for e in client.get(url).json() if e["week"] is not None]
    assert len(biweekly) == 1
    w = biweekly[0]["week"]
    # 1-nji sentýabryň hepdesi 1-nji hepde, indiki hepde 2-nji, ondan soňky ýene 1-nji.
    on_first = client.get(f"{url}?on=2026-09-03").json()
    on_second = client.get(f"{url}?on=2026-09-08").json()
    assert any(e["week"] == w for e in (on_first if w == 1 else on_second))
    assert not any(e["week"] == w for e in (on_second if w == 1 else on_first))
    assert client.get(f"{url}?on=2026-09-15").json() == on_first
