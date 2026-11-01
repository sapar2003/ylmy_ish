from app.seed import seed
from app.services.accounts import ensure_admin
from tests.conftest import client_session_factory


def login(c, username, password):
    r = c.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, r.json()


def setup(c):
    with client_session_factory[0]() as db:
        seed(db)
        password = ensure_admin(db)
    admin, me = login(c, "admin", password)
    assert me["role"] == "admin" and me["must_change_password"]
    return admin


def test_admin_api_is_closed_without_login(anon_client):
    c = anon_client
    assert c.get("/api/v1/faculties").status_code == 401
    assert c.post("/api/v1/auth/login", json={"username": "admin", "password": "x"}).status_code == 401
    admin = setup(c)
    assert c.get("/api/v1/faculties", headers=admin).status_code == 200
    assert c.get("/api/v1/faculties", headers={"Authorization": "Bearer bozuk.token"}).status_code == 401
    # Word ýüklemek ýaly brauzer salgylary üçin token parametr hökmünde hem kabul edilýär.
    token = admin["Authorization"].split()[1]
    assert c.get(f"/api/v1/faculties?token={token}").status_code == 200


def test_teacher_sees_only_own_published_timetable(anon_client):
    c = anon_client
    admin = setup(c)
    issued = c.post("/api/v1/users/teachers", json={}, headers=admin).json()
    teachers = c.get("/api/v1/teachers?limit=500", headers=admin).json()["items"]
    assert len(issued) == len(teachers)
    assert c.post("/api/v1/users/teachers", json={}, headers=admin).json() == []  # ikinji gezek hasap açylmaýar
    assert len({i["username"] for i in issued}) == len(issued)

    acc = next(i for i in issued if i["teacher"]["name"] == "A. Annaýew")
    teacher, me = login(c, acc["username"], acc["password"])
    assert me["role"] == "teacher" and me["teacher"]["name"] == "A. Annaýew" and me["must_change_password"]

    # Mugallym admin API-ni ulanyp bilmeýär.
    assert c.get("/api/v1/teachers", headers=teacher).status_code == 403
    assert c.post("/api/v1/users/teachers", json={}, headers=teacher).status_code == 403

    # Çap edilen raspisaniýe ýok.
    assert c.get("/api/v1/me/timetable", headers=teacher).json()["timetable"] is None

    tt = c.post("/api/v1/timetables", json={"name": "Güýz", "time_limit_seconds": 20, "weeks": 2,
                                           "starts_on": "2026-09-01"}, headers=admin).json()
    assert c.post(f"/api/v1/timetables/{tt['id']}/publish", json={"published": True}, headers=admin).json()[
        "published"]
    week1 = c.get("/api/v1/me/timetable?on=2026-09-02", headers=teacher).json()
    week2 = c.get("/api/v1/me/timetable?on=2026-09-09", headers=teacher).json()
    assert week1["timetable"]["id"] == tt["id"] and week1["week"] == 1 and week2["week"] == 2
    assert week1["week_start"] == "2026-08-31"
    assert week1["entries"] and all(e["teacher"]["name"] == "A. Annaýew" for e in week1["entries"] + week2["entries"])
    everyone = c.get(f"/api/v1/timetables/{tt['id']}/entries", headers=admin).json()
    assert len(everyone) > len(week1["entries"])

    # Paroly çalyşmak.
    assert c.post("/api/v1/auth/change-password", json={"old_password": "nädogry", "new_password": "taze123"},
                  headers=teacher).status_code == 422
    r = c.post("/api/v1/auth/change-password", json={"old_password": acc["password"], "new_password": "taze123"},
               headers=teacher)
    assert r.status_code == 200 and not r.json()["must_change_password"]
    login(c, acc["username"], "taze123")

    # Admin paroly täzeläp biler.
    new = c.post(f"/api/v1/users/{acc['user_id']}/reset-password", headers=admin).json()
    login(c, acc["username"], new["password"])
