import numpy as np
import pytest

from app.ml.risk import assess, load_artifact


def steady(days=60, minutes=45):
    return np.full(days, float(minutes))


def went_quiet(days=60, quiet=20):
    series = steady(days)
    series[-quiet:] = 0
    return series


def test_artifact_is_well_formed():
    a = load_artifact()
    n = len(a["features"])
    assert len(a["mean"]) == len(a["scale"]) == len(a["coef"]) == n
    assert a["calibrator"]["x"] == sorted(a["calibrator"]["x"])
    assert 0 < a["base_rate"] < 0.2 and 0 < a["levels"]["elevated"] < a["levels"]["high"] < 1
    assert a["test_metrics"]["roc_auc"] > 0.65  # guards against shipping a broken retrain


def test_cold_start_refuses_to_guess():
    assert assess(steady(10), []).status == "insufficient_data"
    sparse = np.zeros(40)
    sparse[[3, 9]] = 30
    r = assess(sparse, [])
    assert r.status == "insufficient_data" and r.probability is None and "keep logging" in r.message.lower()


def test_going_quiet_is_riskier_than_staying_steady():
    steady_r, quiet_r = assess(steady(), []), assess(went_quiet(), [])
    assert steady_r.status == quiet_r.status == "ok"
    assert quiet_r.probability > steady_r.probability
    assert quiet_r.level in {"elevated", "high"} and steady_r.level == "low"


def test_probability_is_a_probability_and_close_to_training_base_rate_scale():
    for daily in (steady(), went_quiet(), went_quiet(quiet=35)):
        p = assess(daily, []).probability
        assert 0.0 <= p <= 1.0 and p < 0.5  # the model is calibrated to ~3% base rates, not near-certainty


def test_unit_change_does_not_change_the_answer_much():
    daily = np.array([10, 0, 25, 0, 40, 5, 0] * 9, dtype=float)
    a, b = assess(daily, []).probability, assess(daily * 60, []).probability
    assert a == pytest.approx(b, abs=0.003)


def test_drivers_explain_a_drop_in_plain_language():
    r = assess(went_quiet(), [])
    raising = [d for d in r.drivers if d.effect == "raises"]
    assert raising, "a student who went quiet should have at least one risk-raising driver"
    text = " ".join(d.detail for d in r.drivers)
    assert "last session" in text or "of the last 14 days" in text
    assert all(d.weight >= 0.05 for d in r.drivers)
    assert r.drivers == sorted(r.drivers, key=lambda d: d.weight, reverse=True)


def test_good_scores_lower_risk_and_poor_scores_raise_it():
    good = assess(steady(), [(10, 0.9), (30, 0.85), (50, 0.9)]).probability
    poor = assess(steady(), [(10, 0.3), (30, 0.25), (50, 0.2)]).probability
    assert good < poor


def test_response_never_contains_free_text_or_identifiers():
    r = assess(went_quiet(), [(5, 0.5)])
    blob = repr(r)
    assert "@" not in blob and "email" not in blob.lower()


def test_no_scores_is_not_treated_as_a_risk_signal():
    r = assess(steady(), [])
    assert all(d.label != "Scores" for d in r.drivers)
    with_scores = assess(steady(), [(10, 0.76), (30, 0.76)])  # exactly average scores: should barely move it
    assert abs(with_scores.probability - r.probability) < 0.004
