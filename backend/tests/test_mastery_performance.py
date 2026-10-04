from datetime import UTC, datetime, timedelta

import pytest

from app.ml.mastery import HALF_LIFE_DAYS, Evidence, estimate, fade, rating_to_fraction
from app.ml.performance import TopicPosterior, predict

NOW = datetime(2026, 10, 4, tzinfo=UTC)


def ev(fraction, strength, days_ago=0.0):
    return Evidence(fraction, strength, NOW - timedelta(days=days_ago))


def test_no_evidence_is_the_uniform_prior():
    m = estimate([], NOW)
    assert m.mean == pytest.approx(0.5) and m.evidence == 0 and m.n_observations == 0
    assert m.lo < 0.06 and m.hi > 0.94 and m.last_evidence_at is None


def test_conjugate_update_matches_hand_calculation():
    # 8 of 10 effective questions right: Beta(1+8, 1+2).
    m = estimate([ev(0.8, 10)], NOW)
    assert (m.a, m.b) == pytest.approx((9.0, 3.0)) and m.mean == pytest.approx(0.75)


def test_more_evidence_narrows_the_interval():
    few = estimate([ev(0.7, 4)], NOW)
    many = estimate([ev(0.7, 4)] * 6, NOW)
    assert (many.hi - many.lo) < (few.hi - few.lo)
    assert many.mean == pytest.approx(0.7, abs=0.05)


def test_old_evidence_fades_and_the_interval_widens_again():
    fresh = estimate([ev(0.9, 12, 0)], NOW)
    stale = estimate([ev(0.9, 12, 3 * HALF_LIFE_DAYS)], NOW)
    assert fade(HALF_LIFE_DAYS) == pytest.approx(0.5)
    assert stale.evidence == pytest.approx(12 / 8)  # three half-lives
    assert (stale.hi - stale.lo) > (fresh.hi - fresh.lo)
    assert stale.mean < fresh.mean  # drifts back toward 0.5


def test_recent_result_outweighs_an_old_one():
    m = estimate([ev(0.2, 10, 400), ev(0.9, 10, 1)], NOW)
    assert m.mean > 0.7


def test_future_dated_evidence_is_not_inflated():
    assert fade(-5) == 1.0


def test_rating_mapping_stays_off_the_extremes():
    assert rating_to_fraction(1) == pytest.approx(0.1) and rating_to_fraction(5) == pytest.approx(0.9)


def test_performance_refuses_without_evidence():
    assert predict([TopicPosterior(1, 1, 1, 0.0)]) is None
    assert predict([]) is None


def test_performance_tracks_mastery_and_is_deterministic():
    strong = [TopicPosterior(1, 45, 6, 50), TopicPosterior(1, 40, 8, 46)]
    weak = [TopicPosterior(1, 8, 30, 36), TopicPosterior(1, 9, 28, 35)]
    s, w = predict(strong, seed=1), predict(weak, seed=1)
    assert s.mean > 0.8 > 0.3 > w.mean
    assert s.p_pass > 0.99 > 0.01 > w.p_pass
    assert predict(strong, seed=1) == s
    assert 0 <= s.lo < s.mean < s.hi <= 1


def test_untouched_topics_widen_the_interval_and_show_in_coverage():
    covered = [TopicPosterior(1, 30, 10, 40), TopicPosterior(1, 30, 10, 40)]
    gap = [TopicPosterior(1, 30, 10, 40), TopicPosterior(1, 1, 1, 0)]
    a, b = predict(covered, seed=3), predict(gap, seed=3)
    assert (b.hi - b.lo) > (a.hi - a.lo)
    assert a.covered_weight == pytest.approx(1.0) and b.covered_weight == pytest.approx(0.5)


def test_topic_weights_matter():
    topics = [TopicPosterior(9, 40, 4, 44), TopicPosterior(1, 4, 40, 44)]
    heavy_on_strong = predict(topics, seed=2)
    flipped = predict([TopicPosterior(1, 40, 4, 44), TopicPosterior(9, 4, 40, 44)], seed=2)
    assert heavy_on_strong.mean > 0.7 > 0.3 > flipped.mean
