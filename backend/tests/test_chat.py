from app.core.security import create_token
from app.services.accounts import user_by_phone
from tests.conftest import client_session_factory
from tests.test_users import setup


def _token(phone):
    with client_session_factory[0]() as db:
        return {"Authorization": f"Bearer {create_token(user_by_phone(db, phone).id)}"}


def test_chat_between_teacher_and_own_student(anon_client):
    c = anon_client
    admin = setup(c)
    c.post("/api/v1/students/demo", headers=admin)
    tt = c.post("/api/v1/timetables", json={"name": "Güýz", "time_limit_seconds": 20}, headers=admin).json()
    c.post(f"/api/v1/timetables/{tt['id']}/publish", json={"published": True}, headers=admin)
    entries = c.get(f"/api/v1/timetables/{tt['id']}/entries", headers=admin).json()
    entry = next(e for e in entries if e["subgroup"] is None)
    teacher_id, group_id = entry["teacher"]["id"], entry["groups"][0]["id"]
    students = c.get(f"/api/v1/students?group_id={group_id}&limit=500", headers=admin).json()["items"]
    me, classmate = students[0], students[1]

    # Bu toparyň sapagyna girmeýän mugallym.
    teaching_group = {e["teacher"]["id"] for e in entries if group_id in {g["id"] for g in e["groups"]}}
    stranger = next(t for t in c.get("/api/v1/teachers?limit=500", headers=admin).json()["items"] if t["id"] not in teaching_group)

    for path, phone in ((f"students/{me['id']}", "65300001"), (f"students/{classmate['id']}", "65300002"),
                        (f"teachers/{teacher_id}", "65300003"), (f"teachers/{stranger['id']}", "65300004")):
        assert c.patch(f"/api/v1/{path}", json={"phone": phone}, headers=admin).status_code == 200
    st, st2 = _token("+99365300001"), _token("+99365300002")
    te, te2 = _token("+99365300003"), _token("+99365300004")

    assert c.get("/api/v1/chat/contacts").status_code == 401
    assert c.get("/api/v1/chat/contacts", headers=admin).status_code == 403
    assert teacher_id in {x["id"] for x in c.get("/api/v1/chat/contacts", headers=st).json()}
    assert me["id"] in {x["id"] for x in c.get("/api/v1/chat/contacts", headers=te).json()}

    # Öz mugallymy däl: ýazyp bolmaýar.
    assert c.post(f"/api/v1/chat/{stranger['id']}/messages", json={"text": "salam"}, headers=st).status_code == 403
    assert c.post(f"/api/v1/chat/{me['id']}/messages", json={"text": "salam"}, headers=te2).status_code == 403

    r = c.post(f"/api/v1/chat/{teacher_id}/messages", json={"text": "  Salam, mugallym! "}, headers=st)
    assert r.status_code == 201 and r.json()["mine"] and r.json()["text"] == "Salam, mugallym!"
    assert c.post(f"/api/v1/chat/{teacher_id}/messages", json={"text": "   "}, headers=st).status_code == 422

    assert c.get("/api/v1/chat/unread", headers=te).json()["count"] == 1
    conv = c.get("/api/v1/chat/conversations", headers=te).json()
    assert conv[0]["id"] == me["id"] and conv[0]["unread"] == 1 and conv[0]["last_text"] == "Salam, mugallym!"
    msgs = c.get(f"/api/v1/chat/{me['id']}/messages", headers=te).json()
    assert len(msgs) == 1 and not msgs[0]["mine"]
    assert c.get("/api/v1/chat/unread", headers=te).json()["count"] == 0  # okaldy

    c.post(f"/api/v1/chat/{me['id']}/messages", json={"text": "Salam!"}, headers=te)
    all_msgs = c.get(f"/api/v1/chat/{teacher_id}/messages", headers=st).json()
    assert [(x["text"], x["mine"]) for x in all_msgs] == [("Salam, mugallym!", True), ("Salam!", False)]
    assert all_msgs[0]["read"]  # mugallym okady
    assert c.get(f"/api/v1/chat/{teacher_id}/messages?after={all_msgs[-1]['id']}", headers=st).json() == []

    # Başga talyp bu söhbeti görmeýär.
    assert c.get(f"/api/v1/chat/{teacher_id}/messages", headers=st2).json() == []
    assert c.get("/api/v1/chat/conversations", headers=st2).json() == []
