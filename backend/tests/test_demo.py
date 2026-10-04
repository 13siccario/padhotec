from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models import DemoAccount, Event, StudySession, User
from app.services.demo_data import DEMO_DOMAIN, DEMO_PASSWORD, delete_demo_accounts, seed_demo
from tests.conftest import register

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def login(client, key):
    r = client.post("/auth/login", json={"email": f"{key}@{DEMO_DOMAIN}", "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_every_demo_account_is_marked_and_uses_the_reserved_demo_domain(db_session):
    created = seed_demo(db_session, now=NOW)
    assert len(created) == 26 and {c.archetype for c in created} >= {"steady", "quiet", "new", "improving", "erratic"}
    users = db_session.scalars(select(User)).all()
    assert len(users) == 26 and all(u.is_demo and u.email.endswith("@" + DEMO_DOMAIN) for u in users)
    assert db_session.scalar(select(func.count()).select_from(DemoAccount)) == 26


def test_demo_accounts_can_sign_in_and_are_flagged_by_the_api(client, db_session):
    seed_demo(db_session, now=NOW)
    me = client.get("/auth/me", headers=login(client, "steady")).json()
    assert me["is_demo"] is True
    real = register(client, email="real@example.com")
    assert client.get("/auth/me", headers=real).json()["is_demo"] is False


def test_seeding_is_deterministic_and_idempotent(db_session):
    seed_demo(db_session, seed=11, now=NOW)
    first = db_session.scalar(select(func.count()).select_from(StudySession))
    assert seed_demo(db_session, seed=11, now=NOW) == []  # already there: nothing added
    assert db_session.scalar(select(func.count()).select_from(StudySession)) == first
    seed_demo(db_session, seed=11, now=NOW, reset=True)
    assert db_session.scalar(select(func.count()).select_from(StudySession)) == first  # same seed, same data
    seed_demo(db_session, seed=12, now=NOW, reset=True)
    assert db_session.scalar(select(func.count()).select_from(StudySession)) != first  # different seed differs


def test_reset_and_remove_never_touch_real_accounts(client, db_session):
    real = register(client, email="real@example.com")
    client.post("/courses", json={"name": "Mine"}, headers=real)
    seed_demo(db_session, now=NOW)
    assert delete_demo_accounts(db_session) == 26
    users = db_session.scalars(select(User)).all()
    assert [u.email for u in users] == ["real@example.com"]
    assert client.get("/courses", headers=real).json()[0]["name"] == "Mine"
    # Their pseudonymous events went with them, but the real student's stayed.
    assert db_session.scalar(select(func.count()).select_from(Event)) == 1


def test_showcase_accounts_show_what_they_promise(client, db_session):
    seed_demo(db_session, now=NOW)
    steady = client.get("/insights", headers=login(client, "steady")).json()
    quiet = client.get("/insights", headers=login(client, "quiet")).json()
    new = client.get("/insights", headers=login(client, "new")).json()

    assert steady["risk"]["status"] == "ok" and steady["risk"]["level"] == "low"
    assert len(steady["courses"]) == 2 and all(c["performance"] for c in steady["courses"])
    assert quiet["risk"]["status"] == "ok" and quiet["risk"]["level"] in {"elevated", "high"}
    assert quiet["risk"]["probability"] > steady["risk"]["probability"]
    assert new["risk"]["status"] == "insufficient_data"  # six days of history: cold start


def test_the_steady_demo_has_a_full_plan_and_careers_to_show(client, db_session):
    seed_demo(db_session, now=NOW)
    auth = login(client, "steady")
    plan = client.get("/plan", headers=auth).json()
    assert plan["blocks"] and plan["studied_today"] == 0  # nothing logged "today", so the plan has its full budget
    careers = client.get("/careers", headers=auth).json()
    assert careers["rated_skills"] >= 3 and careers["careers"][0]["readiness_hi"] > careers["careers"][0]["readiness_lo"]


def test_demo_students_see_demo_peers_and_real_students_never_do(client, db_session):
    seed_demo(db_session, now=NOW)
    demo_peers = client.get("/peers", headers=login(client, "steady")).json()
    assert demo_peers["level"] == "course_and_institution" and demo_peers["cohort_size"] >= 5
    real = register(client, email="real@example.com")
    client.post("/courses", json={"name": "Statistics"}, headers=real)
    out = client.get("/peers", headers=real).json()
    assert out["level"] == "public_prior"  # 26 demo students exist, but they are not this student's peers


def test_demo_accounts_are_excluded_from_the_evidence_page(client, db_session):
    seed_demo(db_session, now=NOW)
    for key in ("steady", "quiet"):
        client.get("/insights", headers=login(client, key))  # stores prediction snapshots
    live = client.get("/evaluation").json()["live"]
    assert live["real_students"] == 0 and live["risk"]["snapshots"] == 0 and live["performance"]["snapshots"] == 0


def test_deleting_a_demo_account_through_the_api_removes_its_marker(client, db_session):
    seed_demo(db_session, now=NOW)
    assert client.delete("/auth/me", headers=login(client, "steady")).status_code == 204
    assert db_session.scalar(select(func.count()).select_from(DemoAccount)) == 25
