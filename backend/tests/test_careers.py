import pytest

from app.services.careers import (
    FOUNDATION_LEVEL,
    SkillLevel,
    estimate_skill,
    load_catalog,
    rank_careers,
    readiness,
    skills_by_key,
    validate_catalog,
)


def career(key):
    return next(c for c in load_catalog()["careers"] if c["key"] == key)


def levels_for(key, level):
    """Every skill the career lists, at a fixed level with a narrow interval."""
    return {r["skill"]: SkillLevel(level, level - 3, level + 3) for r in career(key)["requirements"]}


def test_catalogue_is_valid():
    assert validate_catalog(load_catalog()) == []
    assert 5 <= len(load_catalog()["careers"]) <= 10


def test_validator_catches_broken_edits():
    broken = {
        "skills": [{"key": "a", "prereqs": ["b"]}, {"key": "b", "prereqs": ["a"]}],
        "careers": [{"key": "c", "requirements": [{"skill": "zzz", "level": 50, "importance": 2}]}],
    }
    problems = " ".join(validate_catalog(broken))
    assert "cycle" in problems and "unknown skill zzz" in problems


def test_unknown_when_nothing_is_known():
    assert estimate_skill(None, []) is None
    assert estimate_skill(None, [(1.0, 1.0)]) is None  # a topic with no evidence says nothing


def test_self_rating_alone_gives_a_wide_interval_and_topic_evidence_narrows_it():
    rating_only = estimate_skill(4, [])
    with_evidence = estimate_skill(4, [(20.0, 6.0)])
    assert rating_only.mean == pytest.approx(70, abs=0.5)  # a rating of 4 means about 70
    assert (with_evidence.hi - with_evidence.lo) < (rating_only.hi - rating_only.lo)
    assert with_evidence.mean > rating_only.mean  # strong topic results pull the estimate up


def test_topic_evidence_alone_is_enough():
    level = estimate_skill(None, [(15.0, 5.0)])
    assert level is not None and level.mean > 60


def test_meeting_every_requirement_gives_full_readiness_and_no_gaps():
    r = readiness(career("quant_analyst"), levels_for("quant_analyst", 95))
    assert r.mean == pytest.approx(1.0) and r.gaps == [] and r.unrated == 0 and r.roadmap == []


def test_unrated_skills_widen_the_range_instead_of_counting_as_zero_or_met():
    c = career("data_analyst")
    none = readiness(c, {})
    assert (none.lo, none.mean, none.hi) == (0.0, 0.5, 1.0) and none.unrated == none.total
    half = {r["skill"]: SkillLevel(90, 85, 95) for r in c["requirements"][:3]}
    some = readiness(c, half)
    assert some.unrated == 3 and some.lo < some.mean < some.hi
    assert (some.hi - some.lo) < (none.hi - none.lo)


def test_higher_levels_never_lower_readiness():
    low, high = readiness(career("ml_engineer"), levels_for("ml_engineer", 40)), readiness(
        career("ml_engineer"), levels_for("ml_engineer", 75)
    )
    assert high.mean > low.mean and high.lo > low.lo


def test_gaps_are_ordered_by_importance_times_shortfall():
    c = career("quant_analyst")
    levels = levels_for("quant_analyst", 90)
    levels["probability"] = SkillLevel(30, 25, 35)  # importance 3, big shortfall
    levels["optimization"] = SkillLevel(30, 25, 35)  # importance 1, similar shortfall
    r = readiness(c, levels)
    assert [g.skill for g in r.gaps][:2] == ["probability", "optimization"]
    assert r.gaps[0].current == pytest.approx(30)


def test_roadmap_puts_prerequisites_first_and_adds_missing_foundations():
    levels = levels_for("ml_engineer", 90)
    levels["ml"] = SkillLevel(20, 15, 25)
    levels["statistics"] = SkillLevel(25, 20, 30)  # weak, and the foundation for ml
    levels["probability"] = SkillLevel(25, 20, 30)  # weak foundation for statistics
    steps = [s.skill for s in readiness(career("ml_engineer"), levels).roadmap]
    assert steps.index("probability") < steps.index("statistics") < steps.index("ml")


def test_roadmap_pulls_in_a_foundation_the_role_does_not_list():
    c = career("data_scientist")  # lists probability and statistics but not calculus
    assert "calculus" not in {r["skill"] for r in c["requirements"]}
    levels = levels_for("data_scientist", 90)
    levels["probability"] = SkillLevel(30, 25, 35)
    levels["calculus"] = SkillLevel(10, 5, 15)  # not required by the role, but probability builds on it
    steps = readiness(c, levels).roadmap
    names = [s.skill for s in steps]
    assert "calculus" in names and names.index("calculus") < names.index("probability")
    calculus = next(s for s in steps if s.skill == "calculus")
    assert calculus.target == FOUNDATION_LEVEL and "foundation" in calculus.reason.lower()


def test_roadmap_is_capped_and_every_step_has_its_prerequisites_earlier():
    steps = readiness(career("ml_engineer"), {}).roadmap
    assert 0 < len(steps) <= 6
    skills = skills_by_key()
    seen = set()
    for s in steps:
        assert not any(p in {x.skill for x in steps} and p not in seen for p in skills[s.skill]["prereqs"])
        seen.add(s.skill)


def test_ranking_prefers_the_role_the_student_actually_fits():
    levels = {k: SkillLevel(15, 10, 20) for k in skills_by_key()}
    for skill in ("probability", "statistics", "calculus", "linear_algebra", "programming", "time_series", "finance"):
        levels[skill] = SkillLevel(88, 84, 92)
    ranked = rank_careers(levels)
    assert ranked[0].career in {"quant_analyst", "actuarial_analyst"}
    assert ranked[-1].mean < ranked[0].mean
    assert [r.mean for r in ranked] == sorted([r.mean for r in ranked], reverse=True)


def test_a_top_self_rating_can_meet_a_demanding_requirement():
    top = estimate_skill(5, [])
    assert top.mean == pytest.approx(90, abs=0.5) and top.mean >= 80
    r = readiness(career("ml_engineer"), {x["skill"]: estimate_skill(5, []) for x in career("ml_engineer")["requirements"]})
    assert r.gaps == [] and r.mean == pytest.approx(1.0)  # five out of five everywhere means no gaps


def test_each_rating_maps_to_a_distinct_ordered_level_with_wide_uncertainty():
    levels = [estimate_skill(r, []) for r in range(1, 6)]
    assert [round(l.mean) for l in levels] == [10, 30, 50, 70, 90]
    assert all((l.hi - l.lo) > 25 for l in levels[1:4])  # a self-rating alone is not precise
