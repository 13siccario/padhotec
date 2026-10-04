import pytest

from app.services.peers import (
    K_MIN,
    PeerRecord,
    build_peer_insight,
    norm,
    position,
    position_vs_quartiles,
    round_to,
)


def rec(uid, inst="uni a", degree="bsc", courses=None, minutes=120.0, days=3.0):
    courses = {"statistics": frozenset({"bayes", "tests"})} if courses is None else courses
    return PeerRecord(uid, inst, degree, courses, minutes, days)


def crowd(n, **kw):
    return [rec(100 + i, minutes=60 + 10 * i, days=1 + 0.5 * (i % 6), **kw) for i in range(n)]


ME = rec(1, minutes=95.0, days=3.0)


def test_normalisation_and_rounding():
    assert norm("  Intro   to STATISTICS ") == "intro to statistics"
    assert round_to(97, 15) == 90 and round_to(98, 15) == 105 and round_to(2.3, 0.5) == 2.5


def test_position_thirds_and_ties():
    assert position(1, [2, 3, 4, 5, 6, 7]) == "lower third"
    assert position(9, [2, 3, 4, 5, 6, 7]) == "upper third"
    assert position(4.5, [2, 3, 4, 5, 6, 7]) == "middle third"
    assert position(5, [5, 5, 5, 5, 5]) == "middle third"  # identical students sit in the middle
    assert position_vs_quartiles(0.2, 0.5, 3.0) == "lower quarter"
    assert position_vs_quartiles(4, 0.5, 3.0) == "upper quarter" and position_vs_quartiles(1, 0.5, 3.0) == "middle half"


def test_most_specific_group_wins_when_large_enough():
    others = crowd(K_MIN)
    out = build_peer_insight(ME, others, True)
    assert out.status == "ok" and out.level == "course_and_institution" and out.cohort_size == K_MIN


def test_widens_when_the_specific_group_is_too_small():
    same_course_other_uni = crowd(K_MIN, inst="uni b")
    out = build_peer_insight(ME, same_course_other_uni, True)
    assert out.level == "course"  # institution did not match, but the course did
    different_course_same_inst = crowd(K_MIN, courses={"history": frozenset({"rome"})})
    out = build_peer_insight(ME, different_course_same_inst, True)
    assert out.level == "degree"
    assert build_peer_insight(ME, crowd(K_MIN, degree="ba", courses={"history": frozenset({"rome"})}), True).level == "institution"
    assert build_peer_insight(ME, crowd(K_MIN, inst="uni b", degree="ba", courses={"x": frozenset()}), True).level == "everyone"


def test_one_short_of_the_threshold_never_shows_a_peer_group():
    for n in range(0, K_MIN):
        out = build_peer_insight(ME, crowd(n), True)
        assert out.level == "public_prior" and out.cohort_size is None, n


def test_public_prior_is_labelled_and_only_has_the_one_metric():
    out = build_peer_insight(ME, [], True)
    assert out.level == "public_prior" and "public" in out.note.lower() and "not a peer group" in out.note
    assert [m.key for m in out.metrics] == ["active_days_per_week"] and out.common_topics == []
    assert out.metrics[0].position in {"lower quarter", "middle half", "upper quarter"}


def test_values_are_rounded_so_a_quartile_is_not_one_students_exact_figure():
    out = build_peer_insight(ME, crowd(K_MIN), True)
    minutes = next(m for m in out.metrics if m.key == "minutes_per_week")
    assert all(v % 15 == 0 for v in (minutes.p25, minutes.median, minutes.p75))
    days = next(m for m in out.metrics if m.key == "active_days_per_week")
    assert all((v * 2) % 1 == 0 for v in (days.p25, days.median, days.p75))
    assert minutes.you == 95.0  # your own figure is not rounded


def test_no_history_means_no_you_and_a_prompt():
    out = build_peer_insight(ME, crowd(K_MIN), False)
    assert out.metrics[0].you is None and out.metrics[0].position is None and "Log a few weeks" in out.note


def test_output_carries_no_identifiers():
    out = build_peer_insight(ME, crowd(8), True)
    blob = repr(out)
    assert "user_id" not in blob
    assert all(not hasattr(m, "user_id") for m in out.metrics)


def test_common_topics_need_k_students_and_skip_what_you_already_track():
    others = [rec(100 + i, courses={"statistics": frozenset({"bayes", "regression"} | ({"rare"} if i == 0 else set()))})
              for i in range(7)]
    me = rec(1, courses={"statistics": frozenset({"bayes"})})
    out = build_peer_insight(me, others, True)
    names = [t.topic for t in out.common_topics]
    assert names == ["regression"]  # "bayes" is already yours, "rare" has only 1 student
    assert out.common_topics[0].peers_tracking == 7 and out.common_topics[0].cohort_size == 7


def test_common_topics_only_at_course_levels():
    out = build_peer_insight(ME, crowd(K_MIN, courses={"history": frozenset({"rome"})}), True)
    assert out.level == "degree" and out.common_topics == []


def test_topic_counts_below_k_are_hidden_even_in_a_big_group():
    others = [rec(100 + i, courses={"statistics": frozenset({"bayes", "x"} if i < K_MIN - 1 else {"bayes"})})
              for i in range(10)]
    out = build_peer_insight(rec(1, courses={"statistics": frozenset({"bayes"})}), others, True)
    assert out.common_topics == []


def test_missing_institution_never_matches_other_blank_institutions():
    me = rec(1, inst="", degree="", courses={"a": frozenset()})
    others = crowd(K_MIN, inst="", degree="", courses={"b": frozenset()})
    assert build_peer_insight(me, others, True).level == "everyone"  # blank != same institution


def test_above_and_below_average_students_get_different_positions():
    others = crowd(10)
    busy = build_peer_insight(rec(1, minutes=900.0, days=7.0), others, True)
    idle = build_peer_insight(rec(1, minutes=10.0, days=0.5), others, True)
    assert busy.metrics[0].position == "upper third" and idle.metrics[0].position == "lower third"
