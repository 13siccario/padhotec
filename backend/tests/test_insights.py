from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import Prediction
from tests.conftest import register


def days_ago(n: float) -> str:
    return (datetime.now(UTC) - timedelta(days=n)).isoformat()


def setup_course(client, auth, topics=("Bayes", "Tests")):
    course = client.post("/courses", json={"name": "Statistics"}, headers=auth).json()
    made = [client.post(f"/courses/{course['id']}/topics", json={"name": n}, headers=auth).json() for n in topics]
    return course, made


def log_sessions(client, auth, topic_id, n_days=40, every=1, minutes=40, **ratings):
    for d in range(0, n_days, every):
        res = client.post(
            "/sessions",
            json={"topic_id": topic_id, "minutes": minutes, "started_at": days_ago(d), **ratings},
            headers=auth,
        )
        assert res.status_code == 201, res.text


def score(client, auth, course_id, topic_id, points, out_of=10, kind="quiz", ago=1):
    res = client.post(
        "/assessments",
        json={"course_id": course_id, "topic_id": topic_id, "title": "T", "kind": kind,
              "score": points, "max_score": out_of, "taken_at": days_ago(ago)},
        headers=auth,
    )
    assert res.status_code == 201, res.text


def insights(client, auth, **params):
    res = client.get("/insights", headers=auth, params=params)
    assert res.status_code == 200, res.text
    return res.json()


def test_requires_auth_and_validates_pass_mark(client, auth):
    assert client.get("/insights").status_code == 401
    assert client.get("/insights", headers=auth, params={"pass_mark": 0}).status_code == 422
    assert client.get("/insights", headers=auth, params={"pass_mark": 1.5}).status_code == 422


def test_new_user_gets_honest_empty_answers(client, auth):
    data = insights(client, auth)
    assert data["courses"] == []
    assert data["risk"]["status"] == "insufficient_data" and data["risk"]["probability"] is None


def test_course_without_topics_or_evidence_explains_why(client, auth):
    client.post("/courses", json={"name": "Empty"}, headers=auth)
    course, _ = setup_course(client, auth)
    out = insights(client, auth)["courses"]
    assert out[0]["performance"] is None and "Add topics" in out[0]["performance_note"]
    assert out[1]["performance"] is None and "Log a few scores" in out[1]["performance_note"]
    assert all(t["mastery"]["evidence"] == 0 and t["mastery"]["mean"] == 0.5 for t in out[1]["topics"])


def test_scores_drive_mastery_and_the_interval_narrows(client, auth):
    course, (strong, weak) = setup_course(client, auth)
    score(client, auth, course["id"], strong["id"], 9)
    score(client, auth, course["id"], weak["id"], 3)
    first = {t["name"]: t["mastery"] for t in insights(client, auth)["courses"][0]["topics"]}
    assert first["Bayes"]["mean"] > 0.7 > 0.4 > first["Tests"]["mean"]
    for _ in range(3):
        score(client, auth, course["id"], strong["id"], 9)
    later = {t["name"]: t["mastery"] for t in insights(client, auth)["courses"][0]["topics"]}
    assert (later["Bayes"]["hi"] - later["Bayes"]["lo"]) < (first["Bayes"]["hi"] - first["Bayes"]["lo"])
    assert later["Bayes"]["n_observations"] == 4


def test_course_wide_scores_count_for_every_topic_but_less(client, auth):
    course, (a, b) = setup_course(client, auth)
    client.post("/assessments", json={"course_id": course["id"], "title": "Midterm", "kind": "exam",
                                      "score": 9, "max_score": 10}, headers=auth)
    topics = insights(client, auth)["courses"][0]["topics"]
    assert all(t["mastery"]["mean"] > 0.7 and t["mastery"]["n_observations"] == 1 for t in topics)
    direct_course, (c,) = setup_course(client, auth, topics=("Direct",))
    score(client, auth, direct_course["id"], c["id"], 9, kind="exam")
    other = next(x for x in insights(client, auth)["courses"] if x["course_id"] == direct_course["id"])
    assert other["topics"][0]["mastery"]["evidence"] > topics[0]["mastery"]["evidence"]


def test_old_evidence_fades(client, auth):
    course, (t, _) = setup_course(client, auth)
    score(client, auth, course["id"], t["id"], 9, kind="exam", ago=1)
    fresh = insights(client, auth)["courses"][0]["topics"][0]["mastery"]
    client.delete(f"/courses/topics/{t['id']}", headers=auth)
    course2, (t2,) = setup_course(client, auth, topics=("Old",))
    score(client, auth, course2["id"], t2["id"], 9, kind="exam", ago=365)
    old = next(c for c in insights(client, auth)["courses"] if c["course_id"] == course2["id"])["topics"][0]["mastery"]
    assert old["evidence"] < fresh["evidence"] / 8 and old["mean"] < fresh["mean"]


def test_expected_score_appears_with_evidence_and_respects_pass_mark(client, auth):
    course, (a, b) = setup_course(client, auth)
    for topic in (a, b):
        score(client, auth, course["id"], topic["id"], 8, kind="mock")
    perf = insights(client, auth)["courses"][0]["performance"]
    assert 0.6 < perf["mean"] < 0.95 and perf["lo"] < perf["mean"] < perf["hi"]
    assert perf["covered_weight"] == 1.0 and perf["pass_mark"] == 0.5
    strict = insights(client, auth, pass_mark=0.9)["courses"][0]["performance"]
    assert strict["p_pass"] < perf["p_pass"] and strict["pass_mark"] == 0.9


def test_untouched_topic_is_flagged_through_coverage(client, auth):
    course, (a, _) = setup_course(client, auth)
    score(client, auth, course["id"], a["id"], 8, kind="mock")
    assert insights(client, auth)["courses"][0]["performance"]["covered_weight"] == 0.5


def test_self_ratings_count_but_only_the_latest_few(client, auth):
    course, (t, _) = setup_course(client, auth)
    for d in range(10):  # ten glowing ratings, but only five can count
        client.post("/sessions", json={"topic_id": t["id"], "minutes": 30, "confidence_after": 5,
                                       "started_at": days_ago(d)}, headers=auth)
    m = insights(client, auth)["courses"][0]["topics"][0]["mastery"]
    assert m["n_observations"] == 5 and m["mean"] > 0.6
    assert m["evidence"] < 7.5  # five ratings at 1.5 each, before fading


def test_risk_ok_for_a_steady_student_and_higher_after_going_quiet(client, auth):
    course, (t, _) = setup_course(client, auth)
    log_sessions(client, auth, t["id"], n_days=45)
    steady = insights(client, auth)["risk"]
    assert steady["status"] == "ok" and steady["level"] == "low" and steady["horizon_days"] == 28

    quiet_user = register(client, email="quiet@example.com")
    c2, (t2, _) = setup_course(client, quiet_user)
    for d in range(21, 60):  # active until three weeks ago, then nothing
        client.post("/sessions", json={"topic_id": t2["id"], "minutes": 40, "started_at": days_ago(d)},
                    headers=quiet_user)
    quiet = insights(client, quiet_user)["risk"]
    assert quiet["status"] == "ok" and quiet["probability"] > steady["probability"]
    assert any(d["effect"] == "raises" for d in quiet["drivers"])


def test_risk_needs_enough_history(client, auth):
    _, (t, _) = setup_course(client, auth)
    log_sessions(client, auth, t["id"], n_days=5)
    assert insights(client, auth)["risk"]["status"] == "insufficient_data"


def test_snapshots_are_stored_once_per_day_with_the_model_version(client, auth, db_session):
    course, (t, _) = setup_course(client, auth)
    log_sessions(client, auth, t["id"], n_days=40)
    score(client, auth, course["id"], t["id"], 8)
    insights(client, auth)
    insights(client, auth)
    rows = db_session.scalars(select(Prediction)).all()
    assert sorted(r.kind for r in rows) == ["performance", "risk"]  # not four
    risk = next(r for r in rows if r.kind == "risk")
    assert risk.model_version == "risk-oulad-v1" and "days_since_last_activity" in risk.features
    assert next(r for r in rows if r.kind == "performance").course_id == course["id"]


def test_one_student_never_sees_another_students_numbers(client, auth):
    course, (t, _) = setup_course(client, auth)
    score(client, auth, course["id"], t["id"], 10, kind="exam")
    other = register(client, email="other@example.com")
    assert insights(client, other)["courses"] == []


def test_deleting_a_course_or_account_removes_its_snapshots(client, auth, db_session):
    course, (t, _) = setup_course(client, auth)
    log_sessions(client, auth, t["id"], n_days=40)
    score(client, auth, course["id"], t["id"], 8)
    insights(client, auth)
    assert db_session.scalars(select(Prediction)).all()
    assert client.delete(f"/courses/{course['id']}", headers=auth).status_code == 204
    kinds = [r.kind for r in db_session.scalars(select(Prediction))]
    assert kinds == ["risk"]  # the course's performance snapshot went with it
    assert client.delete("/auth/me", headers=auth).status_code == 204
    assert db_session.scalars(select(Prediction)).all() == []
