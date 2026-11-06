import re

from app.services import sms
from app.services.accounts import normalize_phone
from tests.test_users import setup


def _capture(monkeypatch):
    sent = []
    monkeypatch.setattr(sms, "send_sms", lambda phone, text: sent.append((phone, text)))
    return sent


def _student(c, admin, phone="+993 65 123456"):
    group = c.get("/api/v1/groups", headers=admin).json()["items"][0]
    r = c.post("/api/v1/students", json={"full_name": "Aman Saparow", "group_id": group["id"], "phone": phone}, headers=admin)
    assert r.status_code == 201, r.text
    return r.json(), group


def test_normalize_phone():
    assert normalize_phone("65 12-34-56") == "+99365123456"
    assert normalize_phone("+993 65 123456") == "+99365123456"
    assert normalize_phone("123") is None


def test_student_logs_in_with_otp_then_password(anon_client, monkeypatch):
    c = anon_client
    admin = setup(c)
    sent = _capture(monkeypatch)
    st, group = _student(c, admin)
    assert st["phone"] == "+99365123456"

    # Bellenmedik nomere kod iberilmeýär, ýöne jogap birmeňzeş.
    assert c.post("/api/v1/auth/otp/request", json={"phone": "65999999"}).json() == {"ok": True}
    assert sent == []
    assert c.post("/api/v1/auth/otp/request", json={"phone": "12"}).status_code == 422

    assert c.post("/api/v1/auth/otp/request", json={"phone": "65123456"}).json() == {"ok": True}
    assert c.post("/api/v1/auth/otp/request", json={"phone": "65123456"}).json() == {"ok": True}
    assert len(sent) == 1  # minutda bir gezek
    code = re.search(r"\d{6}", sent[0][1]).group()

    # Parol entek ýok: parol bilen girip bolmaýar.
    assert c.post("/api/v1/auth/phone-login", json={"phone": "65123456", "password": "x"}).status_code == 401
    wrong = "000000" if code != "000000" else "111111"
    assert c.post("/api/v1/auth/otp/verify", json={"phone": "65123456", "code": wrong}).status_code == 401
    r = c.post("/api/v1/auth/otp/verify", json={"phone": "65123456", "code": code})
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["role"] == "student" and me["student"]["group_id"] == group["id"] and not me["has_password"]
    assert me["student"]["phone"] == "+99365123456" and me["student"]["course"] == group["course"]
    # Kod bir gezek işleýär.
    assert c.post("/api/v1/auth/otp/verify", json={"phone": "65123456", "code": code}).status_code == 401

    h = {"Authorization": f"Bearer {me['token']}"}
    assert c.get("/api/v1/groups", headers=h).status_code == 403  # talyp admin API-ni ulanyp bilmeýär
    assert c.get(f"/api/v1/public/timetable?group_id={group['id']}", headers=h).status_code == 200

    assert c.post("/api/v1/auth/set-password", json={"new_password": "taze123"}, headers=h).json()["has_password"]
    assert c.post("/api/v1/auth/set-password", json={"new_password": "basga12"}, headers=h).status_code == 409
    r = c.post("/api/v1/auth/phone-login", json={"phone": "+99365123456", "password": "taze123"})
    assert r.status_code == 200 and r.json()["role"] == "student"


def test_wrong_codes_lock_and_duplicate_phone(anon_client, monkeypatch):
    c = anon_client
    admin = setup(c)
    sent = _capture(monkeypatch)
    _student(c, admin)
    c.post("/api/v1/auth/otp/request", json={"phone": "65123456"})
    code = re.search(r"\d{6}", sent[0][1]).group()
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        c.post("/api/v1/auth/otp/verify", json={"phone": "65123456", "code": wrong})
    # 5 ýalňyşdan soň dogry kod hem işlemeýär.
    assert c.post("/api/v1/auth/otp/verify", json={"phone": "65123456", "code": code}).status_code == 401

    teacher = c.get("/api/v1/teachers", headers=admin).json()["items"][0]
    r = c.patch(f"/api/v1/teachers/{teacher['id']}", json={"phone": "65123456"}, headers=admin)
    assert r.status_code == 409  # bir nomer iki adamda bolup bilmez
    assert c.patch(f"/api/v1/teachers/{teacher['id']}", json={"phone": "abc"}, headers=admin).status_code == 422
    assert c.patch(f"/api/v1/teachers/{teacher['id']}", json={"phone": "65111111"}, headers=admin).json()["phone"] == "+99365111111"
    c.post("/api/v1/auth/otp/request", json={"phone": "65111111"})
    code = re.search(r"\d{6}", sent[-1][1]).group()
    me = c.post("/api/v1/auth/otp/verify", json={"phone": "65111111", "code": code}).json()
    assert me["role"] == "teacher" and me["teacher"]["id"] == teacher["id"]
