"""Database glue for the daily plan, skills and careers, and peer insights."""

from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Course,
    DemoAccount,
    PrivacySetting,
    Recommendation,
    StudentProfile,
    StudentSkill,
    StudySession,
    User,
)
from app.schemas import (
    CareerOut,
    CareersOut,
    GapOut,
    PeerMetricOut,
    PeerOut,
    PlanBlockOut,
    PlanOut,
    RoadmapStepOut,
    SkillLevelOut,
    SkillOut,
    TopicSuggestionOut,
)
from app.services import careers as career_logic
from app.services import peers as peer_logic
from app.services.insights import as_utc, load_user_data, topic_masteries
from app.services.planner import NOTE, PlanCourse, PlanTopic, build_plan

PLAN_VERSION = "plan-greedy-v1"
DEFAULT_BUDGET_MINUTES = 45
MIN_BUDGET, MAX_BUDGET = 15, 240
PEER_WINDOW_DAYS = 28
PEER_MIN_HISTORY_DAYS = 14
PEER_MIN_ACTIVE_DAYS = 3


# ---- daily plan --------------------------------------------------------------------------------------------

def default_budget(profile: StudentProfile | None) -> int:
    hours = profile.weekly_study_hours if profile else None
    if not hours:
        return DEFAULT_BUDGET_MINUTES
    return int(min(max(round(hours * 60 / 7 / 5) * 5, MIN_BUDGET), MAX_BUDGET))


def compute_plan(
    db: Session, user: User, now: datetime | None = None, minutes: int | None = None, utc_offset_minutes: int = 0
) -> PlanOut:
    now = now or datetime.now(UTC)
    local_now = now + timedelta(minutes=utc_offset_minutes)
    today = local_now.date()
    courses, sessions, assessments = load_user_data(db, user)
    masteries = topic_masteries(courses, sessions, assessments, now)

    plan_courses = []
    for c in courses:
        days = None
        if c.exam_date:
            days = ((as_utc(c.exam_date) + timedelta(minutes=utc_offset_minutes)).date() - today).days
        plan_courses.append(
            PlanCourse(
                c.id, c.name, days,
                [PlanTopic(t.id, t.name, t.weight, masteries[t.id].mean, masteries[t.id].evidence) for t in c.topics],
            )
        )
    studied_today = sum(
        s.minutes for s in sessions if (as_utc(s.started_at) + timedelta(minutes=utc_offset_minutes)).date() == today
    )
    budget = minutes if minutes is not None else default_budget(user.profile)
    plan = build_plan(plan_courses, budget, studied_today)

    # Keep the first plan offered each day, as offered, so acceptance can be measured later.
    already = db.scalar(
        select(Recommendation.id).where(
            Recommendation.user_id == user.id, Recommendation.kind == "daily_plan", Recommendation.made_on == today
        )
    )
    if not already and plan.blocks:
        db.add(Recommendation(user_id=user.id, kind="daily_plan", made_on=today, model_version=PLAN_VERSION,
                              payload=asdict(plan)))
        db.commit()
    return PlanOut(
        budget_minutes=plan.budget_minutes, studied_today=plan.studied_today, remaining=plan.remaining,
        headline=plan.headline, note=plan.note or NOTE, blocks=[PlanBlockOut(**asdict(b)) for b in plan.blocks],
    )


# ---- skills and careers -----------------------------------------------------------------------------------

def _skill_state(db: Session, user: User, now: datetime):
    """Ratings, tagged topic names, and the estimated level for every catalogue skill."""
    courses, sessions, assessments = load_user_data(db, user)
    masteries = topic_masteries(courses, sessions, assessments, now)
    ratings = {r.skill_key: r.rating for r in db.scalars(select(StudentSkill).where(StudentSkill.user_id == user.id))}
    evidence, names = defaultdict(list), defaultdict(list)
    for c in courses:
        for t in c.topics:
            if t.skill_key:
                m = masteries[t.id]
                evidence[t.skill_key].append((m.a, m.b))
                names[t.skill_key].append(t.name)
    levels = {key: career_logic.estimate_skill(ratings.get(key), evidence.get(key, [])) for key in career_logic.skills_by_key()}
    return ratings, names, levels


def compute_skills(db: Session, user: User, now: datetime | None = None) -> list[SkillOut]:
    ratings, names, levels = _skill_state(db, user, now or datetime.now(UTC))
    out = []
    for key, skill in career_logic.skills_by_key().items():
        lvl = levels[key]
        out.append(SkillOut(
            key=key, label=skill["label"], rating=ratings.get(key),
            level=None if lvl is None else SkillLevelOut(mean=lvl.mean, lo=lvl.lo, hi=lvl.hi),
            topics=names.get(key, []),
        ))
    return out


def compute_careers(db: Session, user: User, now: datetime | None = None) -> CareersOut:
    ratings, names, levels = _skill_state(db, user, now or datetime.now(UTC))
    ranked = career_logic.rank_careers(levels)
    return CareersOut(
        note=career_logic.load_catalog()["note"],
        rated_skills=sum(1 for v in levels.values() if v is not None),
        total_skills=len(levels),
        careers=[
            CareerOut(
                key=r.career, label=r.label, summary=r.summary,
                readiness_mean=r.mean, readiness_lo=r.lo, readiness_hi=r.hi, unrated=r.unrated, total=r.total,
                gaps=[GapOut(**asdict(g)) for g in r.gaps],
                roadmap=[RoadmapStepOut(**asdict(s), your_topics=names.get(s.skill, [])) for s in r.roadmap],
            )
            for r in ranked
        ],
    )


# ---- peers ---------------------------------------------------------------------------------------------------

def _peer_record(user: User, sessions: list[StudySession], today) -> tuple[peer_logic.PeerRecord, bool]:
    dates = [as_utc(s.started_at).date() for s in sessions if as_utc(s.started_at).date() <= today]
    history_days = (today - min(dates)).days + 1 if dates else 0
    window = max(1, min(PEER_WINDOW_DAYS, history_days))
    cutoff = today - timedelta(days=window - 1)
    recent = [(as_utc(s.started_at).date(), s.minutes) for s in sessions if as_utc(s.started_at).date() >= cutoff
              and as_utc(s.started_at).date() <= today]
    minutes = sum(m for _, m in recent)
    active = len({d for d, _ in recent})
    has_history = history_days >= PEER_MIN_HISTORY_DAYS and len(set(dates)) >= PEER_MIN_ACTIVE_DAYS
    profile = user.profile
    record = peer_logic.PeerRecord(
        user_id=user.id,
        institution=peer_logic.norm(profile.institution) if profile else "",
        degree=peer_logic.norm(profile.degree) if profile else "",
        courses={peer_logic.norm(c.name): frozenset(peer_logic.norm(t.name) for t in c.topics) for c in user.courses},
        minutes_per_week=minutes * 7 / window,
        active_days_per_week=active * 7 / window,
        course_display={peer_logic.norm(c.name): c.name.strip() for c in user.courses},
    )
    return record, has_history


def is_opted_out(db: Session, user_id: int) -> bool:
    row = db.get(PrivacySetting, user_id)
    return bool(row and row.peer_stats_opt_out)


def compute_peers(db: Session, user: User, now: datetime | None = None) -> PeerOut:
    now = now or datetime.now(UTC)
    if is_opted_out(db, user.id):
        return PeerOut(status="opted_out", note="You have opted out of peer statistics. Turn them back on in your "
                                                "profile to see them.")
    today = now.date()
    by_user: dict[int, list[StudySession]] = defaultdict(list)
    for s in db.scalars(select(StudySession)):
        by_user[s.user_id].append(s)
    opted_out = {p.user_id for p in db.scalars(select(PrivacySetting)) if p.peer_stats_opt_out}
    demo_ids = {d.user_id for d in db.scalars(select(DemoAccount))}
    me_is_demo = user.id in demo_ids

    me, my_history = _peer_record(user, by_user.get(user.id, []), today)
    others = []
    for other in db.scalars(select(User).where(User.id != user.id)):
        # Synthetic and real students never mix: demo accounts only see demo peers, real students only real ones.
        if other.id in opted_out or (other.id in demo_ids) != me_is_demo:
            continue
        record, has_history = _peer_record(other, by_user.get(other.id, []), today)
        if has_history:
            others.append(record)

    insight = peer_logic.build_peer_insight(me, others, my_history)
    return PeerOut(
        status=insight.status, level=insight.level, label=insight.label, cohort_size=insight.cohort_size,
        metrics=[PeerMetricOut(**asdict(m)) for m in insight.metrics],
        common_topics=[
            TopicSuggestionOut(**{**asdict(t), "topic": t.topic.capitalize()}) for t in insight.common_topics
        ],
        note=insight.note,
    )
