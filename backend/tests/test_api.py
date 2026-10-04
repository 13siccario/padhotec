from sqlalchemy import select

from app.models import Event, User
from tests.conftest import register


def make_topic(client, auth):
    course = client.post("/courses", json={"name": "Statistics"}, headers=auth).json()
    topic = client.post(
        f"/courses/{course['id']}/topics", json={"name": "Bayes", "weight": 2}, headers=auth
    ).json()
    return course, topic


def test_register_requires_consent(client):
    res = client.post(
        "/auth/register", json={"email": "x@example.com", "password": "longenough1", "consent": False}
    )
    assert res.status_code == 400


def test_register_login_me(client):
    register(client)
    assert client.post("/auth/register", json={"email": "A@example.com", "password": "longenough1", "consent": True}).status_code == 409
    token = client.post("/auth/login", json={"email": "a@example.com", "password": "correct-horse"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "a@example.com"
    assert client.post("/auth/login", json={"email": "a@example.com", "password": "wrong-password"}).status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_profile_update_logs_goal_event_without_free_text(client, auth, db_session):
    res = client.put("/profile", json={"goal_type": "exam", "goal_text": "private note"}, headers=auth)
    assert res.status_code == 200 and res.json()["goal_text"] == "private note"
    events = db_session.scalars(select(Event)).all()
    assert [e.type for e in events] == ["GOAL_SET"]
    assert "private note" not in str(events[0].payload)


def test_session_and_assessment_flow_writes_events(client, auth, db_session):
    course, topic = make_topic(client, auth)
    s = client.post("/sessions", json={"topic_id": topic["id"], "minutes": 45, "confidence_before": 2, "confidence_after": 4}, headers=auth)
    assert s.status_code == 201
    a = client.post(
        "/assessments",
        json={"course_id": course["id"], "topic_id": topic["id"], "title": "Quiz 1", "score": 7, "max_score": 10},
        headers=auth,
    )
    assert a.status_code == 201
    types = [e.type for e in db_session.scalars(select(Event).order_by(Event.id))]
    assert types == ["COURSE_ADDED", "SESSION_LOGGED", "ASSESSMENT_RECORDED"]
    assert len(client.get("/sessions", headers=auth).json()) == 1


def test_assessment_validation(client, auth):
    course, topic = make_topic(client, auth)
    other = client.post("/courses", json={"name": "Other"}, headers=auth).json()
    base = {"title": "T", "score": 5, "max_score": 10}
    assert client.post("/assessments", json={**base, "course_id": course["id"], "score": 11}, headers=auth).status_code == 422
    assert client.post("/assessments", json={**base, "course_id": other["id"], "topic_id": topic["id"]}, headers=auth).status_code == 422


def test_users_cannot_touch_each_others_data(client, auth):
    course, topic = make_topic(client, auth)
    intruder = register(client, email="b@example.com")
    assert client.put(f"/courses/{course['id']}", json={"name": "x"}, headers=intruder).status_code == 404
    assert client.post(f"/courses/{course['id']}/topics", json={"name": "x"}, headers=intruder).status_code == 404
    assert client.post("/sessions", json={"topic_id": topic["id"], "minutes": 10}, headers=intruder).status_code == 404
    assert client.get("/courses", headers=intruder).json() == []


def test_delete_my_data_removes_user_and_events(client, auth, db_session):
    _, topic = make_topic(client, auth)
    client.post("/sessions", json={"topic_id": topic["id"], "minutes": 30}, headers=auth)
    other = register(client, email="b@example.com")
    client.post("/courses", json={"name": "Keep me"}, headers=other)

    assert client.delete("/auth/me", headers=auth).status_code == 204
    assert client.get("/auth/me", headers=auth).status_code == 401
    assert db_session.scalars(select(User)).all()[0].email == "b@example.com"
    # Only the other user's COURSE_ADDED event remains.
    assert [e.type for e in db_session.scalars(select(Event))] == ["COURSE_ADDED"]


def test_deleting_topic_and_course_with_logged_data(client, auth):
    course, topic = make_topic(client, auth)
    client.post("/sessions", json={"topic_id": topic["id"], "minutes": 30}, headers=auth)
    client.post(
        "/assessments",
        json={"course_id": course["id"], "topic_id": topic["id"], "title": "Q", "score": 5, "max_score": 10},
        headers=auth,
    )
    assert client.delete(f"/courses/topics/{topic['id']}", headers=auth).status_code == 204
    # The score survives as a course-level assessment; the topic's sessions are gone.
    kept = client.get("/assessments", headers=auth).json()
    assert len(kept) == 1 and kept[0]["topic_id"] is None
    assert client.get("/sessions", headers=auth).json() == []
    assert client.delete(f"/courses/{course['id']}", headers=auth).status_code == 204
    assert client.get("/assessments", headers=auth).json() == []
