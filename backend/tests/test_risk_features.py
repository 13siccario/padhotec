import numpy as np
import pytest

from app.ml.risk_features import FEATURES, MAX_GAP, build_features

F = {name: i for i, name in enumerate(FEATURES)}


def row(daily, scores, t):
    return build_features(np.array(daily, dtype=float), scores, np.array([t]))[0]


def test_steady_student_has_no_change_and_no_gap():
    r = row([30] * 40, [], 35)
    assert r[F["days_since_last_activity"]] == 0
    assert r[F["active_days_14"]] == 14
    assert r[F["active_rate_change"]] == pytest.approx(0)
    assert r[F["activity_ratio_log"]] == pytest.approx(0)
    assert r[F["weeks_since_start"]] == pytest.approx(5)
    assert r[F["has_score"]] == 0 and r[F["n_scores"]] == 0


def test_going_quiet_shows_up_in_every_activity_feature():
    daily = [30] * 21 + [0] * 14
    r = row(daily, [], 35)
    assert r[F["days_since_last_activity"]] == 14
    assert r[F["active_days_14"]] == 0  # the whole 14-day window (days 21..34) is quiet
    assert r[F["active_rate_change"]] < -0.4
    assert r[F["activity_ratio_log"]] < -1


def test_no_activity_ever_hits_the_gap_cap():
    assert row([0] * 40, [], 30)[F["days_since_last_activity"]] == MAX_GAP


def test_features_are_unit_free():
    daily = np.array([5, 0, 12, 7, 0, 0, 9] * 6, dtype=float)
    a = build_features(daily, [], np.array([35]))
    b = build_features(daily * 60, [], np.array([35]))  # minutes instead of clicks
    # Only the +1 smoothing in the volume ratio may differ, and only slightly.
    assert np.allclose(a[:, :3], b[:, :3]) and np.allclose(a[:, 4:], b[:, 4:])
    assert abs(a[0, F["activity_ratio_log"]] - b[0, F["activity_ratio_log"]]) < 0.1


def test_no_future_leakage():
    daily = [10] * 60
    base = row(daily, [(30, 0.9)], 30)
    changed_future = row([10] * 30 + [999] * 30, [(30, 0.1), (45, 0.0)], 30)
    assert np.allclose(base, changed_future)  # score on day 30 is NOT visible at landmark 30


def test_score_features():
    r = row([10] * 60, [(5, 0.8), (12, 0.6), (20, 0.4)], 40)
    assert r[F["n_scores"]] == 3 and r[F["has_score"]] == 1
    assert r[F["mean_score"]] == pytest.approx(0.6)
    assert r[F["score_trend"]] == pytest.approx(0.4 - 0.7)  # latest minus mean of earlier ones


def test_single_score_has_no_trend_and_scores_are_capped_in_count():
    one = row([10] * 60, [(5, 0.9)], 40)
    assert one[F["score_trend"]] == 0 and one[F["mean_score"]] == pytest.approx(0.9)
    many = row([10] * 60, [(d, 0.5) for d in range(1, 16)], 40)
    assert many[F["n_scores"]] == 10


def test_batch_matches_single_rows_and_pads_short_series():
    daily = np.array([3, 0, 8, 2] * 15, dtype=float)
    scores = [(6, 0.7), (25, 0.5)]
    landmarks = np.array([21, 28, 35, 49])
    batch = build_features(daily, scores, landmarks)
    for i, t in enumerate(landmarks):
        assert np.allclose(batch[i], build_features(daily, scores, np.array([t]))[0])
    padded = build_features(daily[:30], scores, np.array([49]))  # series shorter than the landmark
    assert padded[0, F["days_since_last_activity"]] >= 0


def test_rejects_landmarks_with_too_little_history():
    with pytest.raises(ValueError):
        build_features(np.ones(30), [], np.array([10]))


def test_missing_scores_are_neutral_for_the_model():
    from app.ml.risk_features import EXPLANATION_ONLY, MODEL_FEATURES, SCORE_IMPUTE

    r = row([10] * 60, [], 40)
    assert r[F["mean_score"]] == pytest.approx(SCORE_IMPUTE) and r[F["score_trend"]] == 0
    # Having scores at all must not be something the model can lean on.
    assert not set(EXPLANATION_ONLY) & set(MODEL_FEATURES)
