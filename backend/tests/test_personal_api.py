from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import PrivacySetting, Recommendation, StudentSkill, TopicSkill
from tests.conftest import register


def days_ago(n):
    return (datetime.now(UTC) - timedelta(days=n)).isoformat()


def make_course(client, auth, name="Statistics", topics=("Bayes", "Tests", "Regression"), exam_in_days=12):
    exam = (datetime.now(UTC) + timedelta(days=exam_in_days)).isoformat() if exam_in_days is not None else None
    course = client.post("/courses", json={"name": name, "exam_date": exam}, headers=auth).json()
    made = [client.post(f"/courses/{course['id']}/topics", json={"name": n}, headers=auth).json() for n in topics]
    return course, made


def score(client, auth, course, topic, points, kind="quiz", ago=1):
    r = client.post("/assessments", json={"course_id": course["id"], "topic_id": topic["id"], "title": "T", "kind": kind,
                                          "score": points, "max_score": 10, "taken_at": days_ago(ago)}, headers=auth)
    assert r.status_code == 201, r.text


def study(client, auth, topic, n_days=30, minutes=40, every=1):
    for d in range(0, n_days, every):
        r = client.post("/sessions", json={"topic_id": topic["id"], "minutes": minutes, "started_at": days_ago(d)},
                        headers=auth)
        assert r.status_code == 201, r.text


def get(client, auth, path, **params):
    r = client.get(path, headers=auth, params=params)
    assert r.status_code == 200, r.text
    return r.json()


# ---- plan -------------------------------------------------------------------------------------------------

def test_plan_requires_auth_and_validates_inputs(client, auth):
    assert client.get("/plan").status_code == 401
    assert client.get("/plan", headers=auth, params={"minutes": 5}).status_code == 422
    assert client.get("/plan", headers=auth, params={"minutes": 500}).status_code == 422


def test_plan_for_a_new_student_asks_for_a_course(client, auth):
    plan = get(client, auth, "/plan")
    assert plan["blocks"] == [] and "Add a course" in plan["headline"]


def test_plan_starts_with_a_self_test_then_adapts_to_logged_results(client, auth):
    course, (bayes, tests, regression) = make_course(client, auth)
    first = get(client, auth, "/plan", minutes=60)
    assert first["blocks"][0]["kind"] == "diagnose" and "log the score" in first["headline"].lower()
    for t, pts in ((bayes, 9), (tests, 3), (regression, 5)):
        score(client, auth, course, t, pts, kind="mock")
    after = get(client, auth, "/plan", minutes=60)
    assert all(b["kind"] == "practice" for b in after["blocks"])
    minutes = {b["topic_name"]: b["minutes"] for b in after["blocks"]}
    assert minutes["Tests"] > minutes.get("Bayes", 0)  # the weakest topic gets the most time


def test_time_already_studied_today_reduces_the_plan(client, auth):
    course, (bayes, tests, _) = make_course(client, auth)
    for t in (bayes, tests):
        score(client, auth, course, t, 5, kind="mock")
    client.post("/sessions", json={"topic_id": bayes["id"], "minutes": 30}, headers=auth)
    plan = get(client, auth, "/plan", minutes=60)
    assert plan["studied_today"] == 30 and plan["remaining"] == 30
    assert sum(b["minutes"] for b in plan["blocks"]) <= 30


def test_default_budget_comes_from_weekly_study_hours(client, auth):
    make_course(client, auth)
    assert get(client, auth, "/plan")["budget_minutes"] == 45  # nothing set
    client.put("/profile", json={"weekly_study_hours": 14}, headers=auth)
    assert get(client, auth, "/plan")["budget_minutes"] == 120  # 14 h a week is 2 h a day


def test_only_the_first_plan_of_the_day_is_kept_as_offered(client, auth, db_session):
    course, (bayes, tests, regression) = make_course(client, auth)
    get(client, auth, "/plan", minutes=60)
    score(client, auth, course, bayes, 9, kind="mock")
    get(client, auth, "/plan", minutes=60)
    rows = db_session.scalars(select(Recommendation)).all()
    assert len(rows) == 1 and rows[0].kind == "daily_plan" and rows[0].model_version == "plan-greedy-v1"
    assert rows[0].payload["blocks"][0]["kind"] == "diagnose"  # the one offered first, before any score


def test_plans_are_private(client, auth):
    make_course(client, auth)
    other = register(client, email="other@example.com")
    assert "Add a course" in get(client, other, "/plan")["headline"]


# ---- skills ------------------------------------------------------------------------------------------------

def test_skills_start_unrated_and_rating_sets_a_level(client, auth):
    skills = get(client, auth, "/skills")
    assert len(skills) == 19 and all(s["rating"] is None and s["level"] is None for s in skills)
    r = client.put("/skills/statistics", json={"rating": 4}, headers=auth)
    assert r.status_code == 200
    stats = next(s for s in r.json() if s["key"] == "statistics")
    assert stats["rating"] == 4 and 55 < stats["level"]["mean"] < 75 and stats["level"]["lo"] < stats["level"]["hi"]
    cleared = client.put("/skills/statistics", json={"rating": None}, headers=auth).json()
    assert next(s for s in cleared if s["key"] == "statistics")["level"] is None


def test_skill_rating_validation(client, auth):
    assert client.put("/skills/statistics", json={"rating": 6}, headers=auth).status_code == 422
    assert client.put("/skills/statistics", json={"rating": 0}, headers=auth).status_code == 422
    assert client.put("/skills/not_a_skill", json={"rating": 3}, headers=auth).status_code == 404


def test_tagging_a_topic_lets_its_results_build_the_skill_without_a_rating(client, auth):
    course, (bayes, *_) = make_course(client, auth)
    tagged = client.put(f"/courses/topics/{bayes['id']}/skill", json={"skill_key": "probability"}, headers=auth)
    assert tagged.status_code == 200 and tagged.json()["skill_key"] == "probability"
    assert next(s for s in get(client, auth, "/skills") if s["key"] == "probability")["level"] is None  # no evidence yet
    score(client, auth, course, bayes, 9, kind="exam")
    prob = next(s for s in get(client, auth, "/skills") if s["key"] == "probability")
    assert prob["rating"] is None and prob["level"]["mean"] > 70 and prob["topics"] == ["Bayes"]
    assert get(client, auth, "/courses")[0]["topics"][0]["skill_key"] == "probability"


def test_tagging_validation_clearing_and_ownership(client, auth):
    _, (bayes, *_) = make_course(client, auth)
    assert client.put(f"/courses/topics/{bayes['id']}/skill", json={"skill_key": "nope"}, headers=auth).status_code == 422
    client.put(f"/courses/topics/{bayes['id']}/skill", json={"skill_key": "probability"}, headers=auth)
    cleared = client.put(f"/courses/topics/{bayes['id']}/skill", json={"skill_key": None}, headers=auth)
    assert cleared.json()["skill_key"] is None
    intruder = register(client, email="x@example.com")
    assert client.put(f"/courses/topics/{bayes['id']}/skill", json={"skill_key": "probability"}, headers=intruder).status_code == 404


def test_deleting_a_topic_removes_its_skill_tag(client, auth, db_session):
    _, (bayes, *_) = make_course(client, auth)
    client.put(f"/courses/topics/{bayes['id']}/skill", json={"skill_key": "probability"}, headers=auth)
    assert db_session.scalars(select(TopicSkill)).all()
    assert client.delete(f"/courses/topics/{bayes['id']}", headers=auth).status_code == 204
    assert db_session.scalars(select(TopicSkill)).all() == []


# ---- careers -----------------------------------------------------------------------------------------------

def test_careers_with_no_information_are_honestly_uncertain(client, auth):
    data = get(client, auth, "/careers")
    assert data["rated_skills"] == 0 and data["total_skills"] == 19 and "NOT derived from labour-market" in data["note"]
    assert len(data["careers"]) == 8
    for c in data["careers"]:
        assert (c["readiness_lo"], c["readiness_mean"], c["readiness_hi"]) == (0.0, 0.5, 1.0) and c["unrated"] == c["total"]


def test_rating_skills_moves_the_ranking_and_narrows_the_range(client, auth):
    for key in ("probability", "statistics", "calculus", "linear_algebra", "programming", "time_series", "finance"):
        client.put(f"/skills/{key}", json={"rating": 5}, headers=auth)
    data = get(client, auth, "/careers")
    assert data["careers"][0]["key"] in {"quant_analyst", "actuarial_analyst"}
    top = data["careers"][0]
    assert top["readiness_hi"] - top["readiness_lo"] < 1.0 and top["unrated"] < top["total"]
    assert [c["readiness_mean"] for c in data["careers"]] == sorted((c["readiness_mean"] for c in data["careers"]), reverse=True)


def test_roadmap_points_at_topics_you_already_track(client, auth):
    course, (bayes, *_) = make_course(client, auth)
    client.put(f"/courses/topics/{bayes['id']}/skill", json={"skill_key": "probability"}, headers=auth)
    client.put("/skills/probability", json={"rating": 2}, headers=auth)
    client.put("/skills/statistics", json={"rating": 2}, headers=auth)
    career = next(c for c in get(client, auth, "/careers")["careers"] if c["key"] == "data_scientist")
    step = next(s for s in career["roadmap"] if s["skill"] == "probability")
    assert step["your_topics"] == ["Bayes"] and step["current"] < step["target"]
    order = [s["skill"] for s in career["roadmap"]]
    assert order.index("probability") < order.index("statistics")  # foundation first


# ---- peers and privacy -------------------------------------------------------------------------------------

def make_peer(client, i, institution="Uni A", n_days=30, course="Statistics", topics=("Bayes", "Tests")):
    auth = register(client, email=f"peer{i}@example.com")
    client.put("/profile", json={"institution": institution}, headers=auth)
    _, made = make_course(client, auth, name=course, topics=topics)
    study(client, auth, made[0], n_days=n_days, minutes=20 + 10 * i)
    return auth


def test_alone_you_get_the_labelled_public_benchmark(client, auth):
    _, (bayes, *_) = make_course(client, auth)
    study(client, auth, bayes, n_days=30)
    out = get(client, auth, "/peers")
    assert out["level"] == "public_prior" and out["cohort_size"] is None
    assert "not a peer group" in out["note"] and [m["key"] for m in out["metrics"]] == ["active_days_per_week"]
    assert out["metrics"][0]["you"] is not None and out["common_topics"] == []


def test_peer_group_appears_only_at_five_comparable_students(client, auth):
    _, (bayes, *_) = make_course(client, auth)
    client.put("/profile", json={"institution": "Uni A"}, headers=auth)
    study(client, auth, bayes, n_days=30)
    for i in range(4):
        make_peer(client, i)
        assert get(client, auth, "/peers")["level"] == "public_prior", f"{i + 1} peers must not form a group"
    make_peer(client, 4)
    out = get(client, auth, "/peers")
    assert out["level"] == "course_and_institution" and out["cohort_size"] == 5
    assert {m["key"] for m in out["metrics"]} == {"minutes_per_week", "active_days_per_week"}
    assert all(m["position"] in {"lower third", "middle third", "upper third"} for m in out["metrics"])


def test_peers_without_enough_history_do_not_count(client, auth):
    _, (bayes, *_) = make_course(client, auth)
    study(client, auth, bayes, n_days=30)
    for i in range(5):
        make_peer(client, i, n_days=2)  # only two days of activity each
    assert get(client, auth, "/peers")["level"] == "public_prior"


def test_opting_out_removes_you_from_others_and_hides_peers_from_you(client, auth):
    _, (bayes, *_) = make_course(client, auth)
    study(client, auth, bayes, n_days=30)
    peers = [make_peer(client, i, institution="") for i in range(5)]
    assert get(client, auth, "/peers")["cohort_size"] == 5
    assert client.put("/privacy", json={"peer_stats_opt_out": True}, headers=peers[0]).json() == {"peer_stats_opt_out": True}
    assert get(client, auth, "/peers")["level"] == "public_prior"  # only 4 left, below the threshold
    assert get(client, peers[0], "/peers")["status"] == "opted_out"
    assert get(client, peers[0], "/privacy") == {"peer_stats_opt_out": True}
    client.put("/privacy", json={"peer_stats_opt_out": False}, headers=peers[0])
    assert get(client, auth, "/peers")["cohort_size"] == 5


def test_common_topics_are_suggested_only_when_five_students_track_them(client, auth):
    _, (bayes, *_) = make_course(client, auth, topics=("Bayes",))
    study(client, auth, bayes, n_days=30)
    client.put("/profile", json={"institution": "Uni A"}, headers=auth)
    for i in range(5):
        make_peer(client, i, topics=("Bayes", "Regression"))
    out = get(client, auth, "/peers")
    assert [t["topic"] for t in out["common_topics"]] == ["Regression"]
    assert out["common_topics"][0]["course"] == "Statistics"  # your own spelling, not the normalised form
    assert out["common_topics"][0]["peers_tracking"] == 5 and out["common_topics"][0]["cohort_size"] == 5


def test_peer_response_leaks_no_identities(client, auth):
    _, (bayes, *_) = make_course(client, auth)
    study(client, auth, bayes, n_days=30)
    for i in range(6):
        make_peer(client, i)
    text = client.get("/peers", headers=auth).text
    assert "@" not in text and "peer0" not in text and "user_id" not in text and "email" not in text.lower()


def test_account_deletion_removes_skills_privacy_and_recommendations(client, auth, db_session):
    course, (bayes, tests, _) = make_course(client, auth)
    client.put("/skills/statistics", json={"rating": 3}, headers=auth)
    client.put("/privacy", json={"peer_stats_opt_out": True}, headers=auth)
    score(client, auth, course, bayes, 7, kind="mock")
    get(client, auth, "/plan", minutes=60)
    assert db_session.scalars(select(StudentSkill)).all() and db_session.scalars(select(Recommendation)).all()
    assert client.delete("/auth/me", headers=auth).status_code == 204
    for table in (StudentSkill, PrivacySetting, Recommendation):
        assert db_session.scalars(select(table)).all() == [], table.__name__


def test_plan_works_for_a_student_whose_only_topic_has_no_results_yet(client, auth):
    """Regression: this used to be a 500 on the dashboard."""
    _, (only,) = make_course(client, auth, topics=("Only topic",))
    for d in range(1, 11):  # history up to yesterday, so nothing counts as studied today
        client.post("/sessions", json={"topic_id": only["id"], "minutes": 40, "started_at": days_ago(d)}, headers=auth)
    r = client.get("/plan", headers=auth)
    assert r.status_code == 200
    plan = r.json()
    assert [b["kind"] for b in plan["blocks"]] == ["diagnose"] and "Only topic" in plan["headline"]
