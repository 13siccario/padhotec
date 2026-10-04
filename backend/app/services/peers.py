"""Peer insights with a privacy ladder. The ranking and aggregation here are pure; gathering records is separate.

Rules that make this safe to show:
- A comparison group needs at least K_MIN other students. If the most specific group is too small, widen it
  (same course, then degree, then institution, then everyone). If even everyone is too small, fall back to a
  labelled public-dataset benchmark, and if that does not apply, show nothing.
- Only aggregates leave this module: rounded quartiles, a position band, and topic names that at least K_MIN
  students track. Never a name, an id, or one student's exact figures.
- Students who opted out are neither counted nor shown peer statistics.
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

K_MIN = 5
MINUTES_STEP = 15  # rounding keeps a quartile from being one particular student's exact figure
DAYS_STEP = 0.5
MAX_TOPICS_PER_COURSE = 5
PRIOR_PATH = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "peer_prior_oulad.json"


def norm(text: str) -> str:
    return " ".join(text.lower().split())


@dataclass(frozen=True)
class PeerRecord:
    user_id: int
    institution: str  # normalised, "" if unset
    degree: str
    courses: dict[str, frozenset[str]]  # normalised course name -> normalised topic names
    minutes_per_week: float
    active_days_per_week: float
    # normalised course name -> how this student typed it. Only ever used to show a student their own courses.
    course_display: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MetricOut:
    key: str
    label: str
    unit: str
    you: float | None
    p25: float
    median: float
    p75: float
    position: str | None  # peers: "lower/middle/upper third"; public prior: "lower quarter/middle half/upper quarter"


@dataclass(frozen=True)
class TopicSuggestion:
    course: str
    topic: str
    peers_tracking: int
    cohort_size: int


@dataclass(frozen=True)
class PeerInsight:
    status: str  # "ok" | "opted_out" | "none"
    level: str | None = None
    label: str | None = None
    cohort_size: int | None = None
    metrics: list[MetricOut] = field(default_factory=list)
    common_topics: list[TopicSuggestion] = field(default_factory=list)
    note: str | None = None


@lru_cache(maxsize=1)
def load_prior(path: Path = PRIOR_PATH) -> dict:
    return json.loads(path.read_text())


def round_to(x: float, step: float) -> float:
    return round(round(x / step) * step, 2)


def position(you: float, peers: list[float]) -> str:
    """Where `you` sits among peers, as a third. Ties count half, so identical students land in the middle."""
    below = sum(p < you for p in peers) + 0.5 * sum(p == you for p in peers)
    share = below / len(peers)
    return "lower third" if share < 1 / 3 else "upper third" if share > 2 / 3 else "middle third"


def position_vs_quartiles(you: float, p25: float, p75: float) -> str:
    return "lower quarter" if you < p25 else "upper quarter" if you > p75 else "middle half"


def _levels(me: PeerRecord, others: list[PeerRecord]):
    shares_course = lambda o: bool(set(me.courses) & set(o.courses))  # noqa: E731
    same_inst = lambda o: bool(me.institution) and o.institution == me.institution  # noqa: E731
    same_degree = lambda o: same_inst(o) and bool(me.degree) and o.degree == me.degree  # noqa: E731
    return [
        ("course_and_institution", "Students on the same course at your institution",
         [o for o in others if shares_course(o) and same_inst(o)]),
        ("course", "Students on the same course", [o for o in others if shares_course(o)]),
        ("degree", "Students in your degree", [o for o in others if same_degree(o)]),
        ("institution", "Students at your institution", [o for o in others if same_inst(o)]),
        ("everyone", "All Padhotec students", list(others)),
    ]


def _metric(key, label, unit, step, you, values) -> MetricOut:
    q25, q50, q75 = np.quantile(values, [0.25, 0.5, 0.75])
    return MetricOut(
        key=key, label=label, unit=unit,
        you=None if you is None else round(you, 1),
        p25=round_to(float(q25), step), median=round_to(float(q50), step), p75=round_to(float(q75), step),
        position=None if you is None else position(you, values),
    )


def _common_topics(me: PeerRecord, cohort: list[PeerRecord]) -> list[TopicSuggestion]:
    out = []
    for course, mine in me.courses.items():
        group = [o for o in cohort if course in o.courses]
        if len(group) < K_MIN:
            continue
        counts: dict[str, int] = {}
        for o in group:
            for topic in o.courses[course]:
                counts[topic] = counts.get(topic, 0) + 1
        rows = [(t, n) for t, n in counts.items() if n >= K_MIN and t not in mine]
        rows.sort(key=lambda r: (-r[1], r[0]))
        shown = me.course_display.get(course, course)
        out += [TopicSuggestion(shown, t, n, len(group)) for t, n in rows[:MAX_TOPICS_PER_COURSE]]
    return out


def build_peer_insight(me: PeerRecord, others: list[PeerRecord], has_history: bool) -> PeerInsight:
    """`others` must already exclude `me` and anyone who opted out or has too little history to compare."""
    you_minutes = me.minutes_per_week if has_history else None
    you_days = me.active_days_per_week if has_history else None

    for level, label, group in _levels(me, others):
        if len(group) >= K_MIN:
            metrics = [
                _metric("minutes_per_week", "Study time per week", "minutes", MINUTES_STEP, you_minutes,
                        [o.minutes_per_week for o in group]),
                _metric("active_days_per_week", "Days studied per week", "days", DAYS_STEP, you_days,
                        [o.active_days_per_week for o in group]),
            ]
            topics = _common_topics(me, group) if level in ("course_and_institution", "course") else []
            note = None if has_history else "Log a few weeks of study to see where you sit."
            return PeerInsight("ok", level, label, len(group), metrics, topics, note)

    prior = load_prior()
    q = (prior["p25"], prior["p50"], prior["p75"])
    metric = MetricOut(
        key="active_days_per_week", label="Days active per week", unit="days",
        you=None if you_days is None else round(you_days, 1),
        p25=q[0], median=q[1], p75=q[2],
        position=None if you_days is None else position_vs_quartiles(you_days, q[0], q[2]),
    )
    return PeerInsight(
        "ok", "public_prior", "Students in a public university dataset (OULAD)", None, [metric], [],
        "Too few Padhotec students are comparable to you yet, so this uses a public dataset of distance-learning "
        "students instead. It is a rough benchmark, not a peer group.",
    )
