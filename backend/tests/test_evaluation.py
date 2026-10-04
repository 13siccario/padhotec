from datetime import UTC, date, datetime, timedelta

from app.models import Assessment, Course, Prediction, StudySession, Topic, User
from app.services.evaluation import LIMITATIONS, MIN_PERFORMANCE_RESOLVED, MIN_RISK_RESOLVED, live_evaluation

TODAY = date(2026, 10, 4)
NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def test_evidence_is_public_and_complete(client):
    r = client.get("/evaluation")  # no sign-in
    assert r.status_code == 200
    d = r.json()
    assert d["available"] is True and d["source"].startswith("OULAD")
    h = d["risk"]["headline"]
    assert 0.65 < h["roc_auc"]["value"] < 0.8 and h["roc_auc"]["ci95"][0] < h["roc_auc"]["value"] < h["roc_auc"]["ci95"][1]
    assert h["brier_skill_vs_naive"]["ci95"][0] > 0  # the model beats the naive predictor reliably, if only slightly
    assert h["calibration_slope"] is not None and h["rows_tested"] > 100_000
    assert [m["key"] for m in d["risk"]["models"]] == [
        "baseline_week_only", "baseline_inactivity_gap", "padhotec_model_calibrated", "reference_gradient_boosting"]
    assert len(d["risk"]["calibration"]) >= 8 and set(d["risk"]["level_bands"]) == {"low", "elevated", "high"}
    assert d["risk"]["auc_gain_vs_inactivity_gap"]["ci95"][0] > 0


def test_the_wording_on_the_page_is_backed_by_the_numbers(client):
    d = client.get("/evaluation").json()
    perf = d["performance"]
    # The page says the score estimate is slightly worse than a plain average. Fail if a retrain makes that untrue.
    assert perf["mae_diffs"]["vs_mean_of_earlier"]["ci95"][0] > 0
    assert any("slightly worse than a plain average" in text for text in LIMITATIONS)
    # It also says the estimate beats the naive baselines.
    assert perf["mae_diffs"]["vs_global_mean"]["ci95"][1] < 0 and perf["mae_diffs"]["vs_last_score"]["ci95"][1] < 0
    # And that the 80% range is honest: close to 80% of outcomes.
    assert abs(perf["coverage"]["value"] - 0.8) < 0.02
    assert perf["defaults"] == {"half_life_days": 90.0, "noise_sd": 0.1}
    bands = d["risk"]["level_bands"]
    assert bands["low"]["observed_rate"] < bands["elevated"]["observed_rate"] < bands["high"]["observed_rate"]


def test_limitations_are_stated_and_cover_the_big_caveats(client):
    text = " ".join(client.get("/evaluation").json()["limitations"]).lower()
    for phrase in ("carry over", "modest predictor", "hand-built", "differential privacy", "demo accounts", "synthetic"):
        assert phrase in text, phrase


def real_user(db, i):
    u = User(email=f"u{i}@example.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


def test_live_risk_is_hidden_until_there_are_enough_resolved_predictions(db_session):
    made = TODAY - timedelta(days=40)
    for i in range(MIN_RISK_RESOLVED - 1):
        u = real_user(db_session, i)
        db_session.add(Prediction(user_id=u.id, kind="risk", made_on=made, model_version="v", value={"probability": 0.05}))
    db_session.commit()
    live = live_evaluation(db_session, now=NOW)["risk"]
    assert live["resolved"] == MIN_RISK_RESOLVED - 1 and live["stopped_rate"] is None  # one short: no rate shown


def test_live_risk_compares_predictions_with_what_students_did(db_session):
    made = TODAY - timedelta(days=40)
    n = MIN_RISK_RESOLVED + 10
    for i in range(n):
        u = real_user(db_session, i)
        db_session.add(Prediction(user_id=u.id, kind="risk", made_on=made, model_version="v", value={"probability": 0.1}))
        topic = None
        if i % 4 == 0:  # a quarter of them kept studying in the 28 days after the prediction
            course = Course(user_id=u.id, name="C")
            db_session.add(course)
            db_session.flush()
            topic = Topic(course_id=course.id, name="T")
            db_session.add(topic)
            db_session.flush()
            db_session.add(StudySession(user_id=u.id, topic_id=topic.id, minutes=30,
                                        started_at=datetime.combine(made + timedelta(days=5), datetime.min.time(), tzinfo=UTC)))
    # A prediction too recent to resolve must not count.
    u = real_user(db_session, 999)
    db_session.add(Prediction(user_id=u.id, kind="risk", made_on=TODAY - timedelta(days=3), model_version="v",
                              value={"probability": 0.9}))
    db_session.commit()
    live = live_evaluation(db_session, now=NOW)["risk"]
    assert live["snapshots"] == n + 1 and live["resolved"] == n
    assert live["stopped_rate"] == 0.75  # 40 students, every fourth kept studying: 30 stopped
    assert live["mean_predicted"] == 0.1


def test_live_performance_coverage_uses_the_first_exam_after_the_prediction(db_session):
    made = TODAY - timedelta(days=20)
    for i in range(MIN_PERFORMANCE_RESOLVED):
        u = real_user(db_session, i)
        course = Course(user_id=u.id, name="C")
        db_session.add(course)
        db_session.flush()
        db_session.add(Prediction(user_id=u.id, kind="performance", course_id=course.id, made_on=made, model_version="v",
                                  value={"mean": 0.6, "lo": 0.5, "hi": 0.7}))
        actual = 0.65 if i % 2 == 0 else 0.9  # half inside the range, half outside
        db_session.add(Assessment(user_id=u.id, course_id=course.id, title="Final", kind="exam", score=actual * 100,
                                  max_score=100, taken_at=NOW - timedelta(days=2)))
        # A quiz is not an exam and must be ignored.
        db_session.add(Assessment(user_id=u.id, course_id=course.id, title="Quiz", kind="quiz", score=1, max_score=10,
                                  taken_at=NOW - timedelta(days=10)))
    db_session.commit()
    live = live_evaluation(db_session, now=NOW)["performance"]
    assert live["resolved"] == MIN_PERFORMANCE_RESOLVED and live["coverage"] == 0.5
    assert abs(live["mean_abs_error"] - (0.05 + 0.3) / 2) < 1e-9


def test_a_prediction_made_after_the_exam_does_not_count(db_session):
    u = real_user(db_session, 1)
    course = Course(user_id=u.id, name="C")
    db_session.add(course)
    db_session.flush()
    db_session.add(Prediction(user_id=u.id, kind="performance", course_id=course.id, made_on=TODAY, model_version="v",
                              value={"mean": 0.6, "lo": 0.5, "hi": 0.7}))
    db_session.add(Assessment(user_id=u.id, course_id=course.id, title="Final", kind="exam", score=60, max_score=100,
                              taken_at=NOW - timedelta(days=5)))
    db_session.commit()
    assert live_evaluation(db_session, now=NOW)["performance"]["resolved"] == 0
