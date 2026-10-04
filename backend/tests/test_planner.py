from app.services.planner import MAX_BLOCK, MIN_BLOCK, PlanCourse, PlanTopic, build_plan


def topic(i, mean, weight=1.0, evidence=20.0):
    return PlanTopic(i, f"T{i}", weight, mean, evidence)


def course(topics, days=14, cid=1, name="Stats"):
    return PlanCourse(cid, name, days, topics)


def minutes(plan):
    return {b.topic_id: b.minutes for b in plan.blocks}


def test_weak_topics_get_more_time_than_strong_ones():
    plan = build_plan([course([topic(1, 0.9), topic(2, 0.3), topic(3, 0.6)])], 60, 0)
    m = minutes(plan)
    assert m[2] > m.get(3, 0) >= m.get(1, 0)
    assert plan.headline == f"Spend {m[2]} minutes on T2."


def test_budget_is_used_in_whole_steps_and_blocks_are_not_tiny():
    for budget in (30, 45, 60, 95, 120):
        plan = build_plan([course([topic(1, 0.2), topic(2, 0.4), topic(3, 0.5), topic(4, 0.7)])], budget, 0)
        total = sum(b.minutes for b in plan.blocks)
        assert budget - 4 <= total <= budget
        assert all(b.minutes >= MIN_BLOCK for b in plan.blocks)


def test_heavier_exam_weight_attracts_more_time():
    plan = build_plan([course([topic(1, 0.5, weight=5), topic(2, 0.5, weight=1)])], 60, 0)
    assert minutes(plan)[1] > minutes(plan).get(2, 0)


def test_sooner_exam_wins_the_time():
    soon = course([topic(1, 0.5)], days=4, cid=1, name="Soon")
    later = course([topic(2, 0.5)], days=60, cid=2, name="Later")
    m = minutes(build_plan([soon, later], 60, 0))
    assert m[1] > m.get(2, 0)


def test_courses_without_an_exam_date_are_planned_but_not_urgent():
    dated = course([topic(1, 0.5)], days=10, cid=1)
    undated = course([topic(2, 0.5)], days=None, cid=2, name="Open")
    m = minutes(build_plan([dated, undated], 60, 0))
    assert m[1] > m.get(2, 0) >= 0
    assert build_plan([undated], 45, 0).blocks  # still gets a plan on its own


def test_finished_courses_are_ignored():
    over = course([topic(1, 0.1)], days=-3)
    plan = build_plan([over], 45, 0)
    assert plan.blocks == [] and "Add a course" in plan.headline


def test_topics_with_no_evidence_get_a_self_test_first():
    plan = build_plan([course([topic(1, 0.5, evidence=0.0), topic(2, 0.3), topic(3, 0.6)])], 60, 0)
    assert plan.blocks[0].kind == "diagnose" and plan.blocks[0].topic_id == 1
    assert plan.blocks[0].minutes == 10 and "log the score" in plan.headline.lower()
    assert 1 not in [b.topic_id for b in plan.blocks if b.kind == "practice"]  # practised after it is measured


def test_self_tests_are_capped_and_never_eat_the_whole_budget():
    blank = [topic(i, 0.5, evidence=0.0) for i in range(1, 6)]
    plan = build_plan([course(blank)], 60, 0)
    assert sum(b.kind == "diagnose" for b in plan.blocks) == 2
    small = build_plan([course(blank)], 20, 0)
    assert sum(b.minutes for b in small.blocks if b.kind == "diagnose") <= 10  # at most half of 20


def test_the_loop_new_evidence_changes_tomorrows_plan():
    before = build_plan([course([topic(1, 0.3), topic(2, 0.3)])], 60, 0)
    after = build_plan([course([topic(1, 0.85), topic(2, 0.3)])], 60, 0)  # topic 1 improved after practice
    assert minutes(after)[2] > minutes(before)[2] and minutes(after).get(1, 0) < minutes(before)[1]


def test_time_already_studied_today_comes_off_the_budget():
    full = sum(b.minutes for b in build_plan([course([topic(1, 0.4), topic(2, 0.5)])], 60, 0).blocks)
    partial = build_plan([course([topic(1, 0.4), topic(2, 0.5)])], 60, 35)
    assert partial.remaining == 25 and sum(b.minutes for b in partial.blocks) <= 25 < full


def test_target_reached_gives_no_blocks_and_a_kind_message():
    plan = build_plan([course([topic(1, 0.4)])], 45, 45)
    assert plan.blocks == [] and plan.remaining == 0 and "reached today's target" in plan.headline


def test_no_courses_or_topics():
    assert "Add a course" in build_plan([], 45, 0).headline
    assert "Add a course" in build_plan([course([])], 45, 0).headline


def test_deterministic_and_reasons_are_specific():
    cs = [course([topic(1, 0.35), topic(2, 0.6)], days=9)]
    a, b = build_plan(cs, 60, 0), build_plan(cs, 60, 0)
    assert a == b
    reason = a.blocks[0].reason
    assert "35%" in reason and "exam in 9 days" in reason and "Stats" in reason and "50%" in reason


def test_single_day_exam_wording():
    plan = build_plan([course([topic(1, 0.5)], days=1)], 45, 0)
    assert "exam in 1 day." in plan.blocks[0].reason


def test_no_single_topic_block_runs_past_the_cap_when_there_is_somewhere_else_to_go():
    plan = build_plan([course([topic(1, 0.2, weight=9), topic(2, 0.6), topic(3, 0.7)])], 120, 0)
    assert all(b.minutes <= MAX_BLOCK for b in plan.blocks)
    assert sum(b.minutes for b in plan.blocks) >= 116  # nothing was dropped, it moved to other topics


def test_cap_is_lifted_when_every_topic_has_hit_it():
    plan = build_plan([course([topic(1, 0.3), topic(2, 0.4)])], 240, 0)
    assert sum(b.minutes for b in plan.blocks) >= 236  # still uses the budget rather than dropping time


def test_property_blocks_are_always_legal_across_many_inputs():
    import random

    rng = random.Random(7)
    for _ in range(400):
        n = rng.randint(2, 6)
        topics = [topic(i, rng.uniform(0.05, 0.95), weight=rng.choice([1, 1, 2, 5]),
                        evidence=rng.choice([0.0, 20.0, 20.0])) for i in range(1, n + 1)]
        budget = rng.choice(range(10, 241, 5))
        plan = build_plan([course(topics, days=rng.choice([None, 2, 10, 45]))], budget, 0)
        total = sum(b.minutes for b in plan.blocks)
        assert total <= budget, (budget, plan.blocks)  # time is never invented
        if any(t.evidence >= 1.0 for t in topics) or len(topics) > 2:  # otherwise the self-tests are the whole plan
            assert total >= budget - 4, (budget, plan.blocks)  # and, with something to practise, never lost
        assert all(b.minutes >= MIN_BLOCK for b in plan.blocks), (budget, plan.blocks)
        assert len({b.topic_id for b in plan.blocks}) == len(plan.blocks)
        n_diag = sum(b.kind == "diagnose" for b in plan.blocks)
        practice_topics, practice_budget = n - n_diag, budget - 10 * n_diag
        if practice_budget <= 40 * practice_topics:  # room to spread among the topics left, so the cap must hold
            assert all(b.minutes <= MAX_BLOCK for b in plan.blocks), (budget, n, plan.blocks)


def test_a_single_topic_with_no_results_gets_just_the_self_test_and_does_not_crash():
    plan = build_plan([course([topic(1, 0.5, evidence=0.0)])], 45, 0)
    assert [(b.topic_id, b.kind, b.minutes) for b in plan.blocks] == [(1, "diagnose", 10)]
    assert plan.headline.startswith("Test yourself on T1")


def test_every_topic_unknown_never_crashes_at_any_budget():
    for n in (1, 2, 3):
        for budget in range(10, 241, 5):
            topics = [topic(i, 0.5, evidence=0.0) for i in range(1, n + 1)]
            plan = build_plan([course(topics)], budget, 0)
            assert sum(b.minutes for b in plan.blocks) <= budget
            if budget >= 20:  # room for at least one self-test
                assert plan.blocks[0].kind == "diagnose"
