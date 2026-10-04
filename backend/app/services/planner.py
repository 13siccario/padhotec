"""Daily study plan: where today's minutes do the most good. Pure functions: no database access.

Each topic has a value  v = urgency x exam share x (1 - mastery),  where urgency rises as the exam nears.
Minutes are handed out in 5-minute steps to whichever topic gains most from the next step, and each topic's
return falls off exponentially, so time spreads across weak topics instead of piling onto one.

Topics with no evidence yet get a short "test yourself and log it" block first. That is the loop: the result
updates mastery, and tomorrow's plan changes with it.

The shape of the return curve (TAU) is a planning heuristic. Nothing here is fitted to learning outcomes.
"""

import math
from dataclasses import dataclass, field

TAU = 60.0  # minutes of study on one topic over which its return falls by about 63%
QUANTUM = 5
MIN_BLOCK = 10
MAX_BLOCK = 45  # past this, switch topic: long single-topic stretches are a poor way to study
DIAGNOSE_MINUTES = 10
MAX_DIAGNOSE = 2
DIAGNOSE_BUDGET_SHARE = 0.5
EVIDENCE_NEEDED = 1.0
URGENCY_MIN_DAYS, URGENCY_MAX_DAYS, NO_EXAM_DAYS = 3, 90, 60

NOTE = "Based on your mastery estimates and exam dates. How time is split is a planning rule, not a prediction."


@dataclass(frozen=True)
class PlanTopic:
    topic_id: int
    name: str
    weight: float
    mean: float  # mastery 0-1
    evidence: float


@dataclass(frozen=True)
class PlanCourse:
    course_id: int
    name: str
    days_to_exam: int | None  # None: no exam date; negative: already passed
    topics: list[PlanTopic]


@dataclass(frozen=True)
class PlanBlock:
    topic_id: int
    topic_name: str
    course_id: int
    course_name: str
    minutes: int
    kind: str  # "diagnose" | "practice"
    reason: str


@dataclass(frozen=True)
class Plan:
    budget_minutes: int
    studied_today: int
    remaining: int
    blocks: list[PlanBlock] = field(default_factory=list)
    headline: str = ""
    note: str = NOTE


def _urgency(days: int | None) -> float:
    d = NO_EXAM_DAYS if days is None else days
    return 1.0 / min(max(d, URGENCY_MIN_DAYS), URGENCY_MAX_DAYS)


def _gain(value: float, minutes_so_far: float) -> float:
    return value * (math.exp(-minutes_so_far / TAU) - math.exp(-(minutes_so_far + QUANTUM) / TAU))


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def build_plan(courses: list[PlanCourse], budget: int, studied_today: int) -> Plan:
    remaining = budget - studied_today
    base = {"budget_minutes": budget, "studied_today": studied_today, "remaining": max(remaining, 0)}

    live = [c for c in courses if c.topics and (c.days_to_exam is None or c.days_to_exam >= 0)]
    if not live:
        return Plan(**base, headline="Add a course with topics to get a daily plan.")
    if remaining < MIN_BLOCK:
        return Plan(**base, headline="You have reached today's target. Anything more is a bonus.")

    # (course, topic, value, share of the course's exam)
    items = []
    for c in live:
        total_weight = sum(t.weight for t in c.topics)
        for t in c.topics:
            share = t.weight / total_weight
            items.append((c, t, _urgency(c.days_to_exam) * share * (1 - t.mean), share))

    # 1. Short self-tests for topics we know nothing about, most important first.
    unknown = sorted((i for i in items if i[1].evidence < EVIDENCE_NEEDED),
                     key=lambda i: (-_urgency(i[0].days_to_exam) * i[3], i[1].topic_id))
    n_diag = min(MAX_DIAGNOSE, len(unknown), int(remaining * DIAGNOSE_BUDGET_SHARE // DIAGNOSE_MINUTES))
    diagnosed = unknown[:n_diag]
    blocks = [
        PlanBlock(t.topic_id, t.name, c.course_id, c.name, DIAGNOSE_MINUTES, "diagnose",
                  "Nothing is logged for this topic yet, so there is nothing to plan from. A short self-test "
                  "fixes that. Log the score afterwards.")
        for c, t, _, _ in diagnosed
    ]

    # 2. Spread the rest where the next 5 minutes help most.
    practice_budget = remaining - DIAGNOSE_MINUTES * n_diag
    skip = {t.topic_id for _, t, _, _ in diagnosed}
    pool = [i for i in items if i[1].topic_id not in skip]
    alloc = {i[1].topic_id: 0 for i in pool}
    # If every topic is getting a self-test, there is nothing to practise yet: the self-tests are the plan.
    for _ in range(practice_budget // QUANTUM if pool else 0):
        eligible = [i for i in pool if alloc[i[1].topic_id] < MAX_BLOCK] or pool  # lift the cap only if all hit it
        best = max(eligible, key=lambda i: (_gain(i[2], alloc[i[1].topic_id]), -i[1].topic_id))
        alloc[best[1].topic_id] += QUANTUM

    # Tiny blocks are not worth the context switch. Top one up from the biggest block if that leaves both
    # legal; otherwise fold it in. Either way no block grows past the cap that was just enforced.
    while True:
        used = {k: v for k, v in alloc.items() if v > 0}
        if len(used) < 2 or min(used.values()) >= MIN_BLOCK:
            break
        small = min(used, key=lambda k: (used[k], k))
        big = max((k for k in used if k != small), key=lambda k: (used[k], -k))  # never the same block
        need = MIN_BLOCK - alloc[small]
        if alloc[big] - need >= MIN_BLOCK:
            alloc[big] -= need
            alloc[small] += need
        else:
            alloc[big] += alloc[small]
            alloc[small] = 0

    by_topic = {i[1].topic_id: i for i in pool}
    practice = []
    for topic_id, minutes in alloc.items():
        if minutes <= 0:
            continue
        c, t, _, share = by_topic[topic_id]
        when = f", exam in {c.days_to_exam} day{'s' if c.days_to_exam != 1 else ''}" if c.days_to_exam is not None else ""
        reason = f"Estimated mastery about {_pct(t.mean)}, and it is {_pct(share)} of the {c.name} exam{when}."
        practice.append(PlanBlock(t.topic_id, t.name, c.course_id, c.name, minutes, "practice", reason))
    practice.sort(key=lambda b: (-b.minutes, b.topic_id))
    blocks += practice

    first = blocks[0]
    headline = (
        f"Test yourself on {first.topic_name} for {first.minutes} minutes, then log the score."
        if first.kind == "diagnose"
        else f"Spend {first.minutes} minutes on {first.topic_name}."
    )
    return Plan(**base, blocks=blocks, headline=headline)
