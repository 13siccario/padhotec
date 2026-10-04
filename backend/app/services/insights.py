"""Turn a student's logged data into mastery, performance and risk, and keep a daily snapshot of each."""

from dataclasses import asdict
from datetime import UTC, date, datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import mastery as mastery_model
from app.ml import risk as risk_model
from app.ml.mastery import (
    ASSESSMENT_STRENGTH,
    COURSE_LEVEL_SHARE,
    MAX_SELF_RATINGS,
    SELF_RATING_STRENGTH,
    Evidence,
    rating_to_fraction,
)
from app.ml.performance import TopicPosterior, predict
from app.models import Assessment, Course, Prediction, StudySession, User
from app.schemas import (
    CourseInsight,
    DriverOut,
    InsightsOut,
    MasteryOut,
    PerformanceOut,
    RiskOut,
    TopicInsight,
)

PERFORMANCE_VERSION = "performance-beta-mc-v1"


def as_utc(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; everything stored is UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _topic_evidence(
    course: Course, topic_id: int, assessments: list[Assessment], sessions: list[StudySession]
) -> list[Evidence]:
    items: list[Evidence] = []
    for a in assessments:
        if a.course_id != course.id or a.max_score <= 0:
            continue
        if a.topic_id == topic_id:
            share = 1.0
        elif a.topic_id is None:
            share = COURSE_LEVEL_SHARE
        else:
            continue
        items.append(
            Evidence(min(a.score / a.max_score, 1.0), ASSESSMENT_STRENGTH.get(a.kind, 4.0) * share, as_utc(a.taken_at))
        )

    rated = [s for s in sessions if s.topic_id == topic_id and (s.confidence_after or s.confidence_before)]
    rated.sort(key=lambda s: as_utc(s.started_at), reverse=True)
    for s in rated[:MAX_SELF_RATINGS]:
        rating = s.confidence_after or s.confidence_before
        items.append(Evidence(rating_to_fraction(rating), SELF_RATING_STRENGTH, as_utc(s.started_at)))
    return items


def load_user_data(db: Session, user: User):
    courses = db.scalars(select(Course).where(Course.user_id == user.id).order_by(Course.id)).all()
    sessions = db.scalars(select(StudySession).where(StudySession.user_id == user.id)).all()
    assessments = db.scalars(select(Assessment).where(Assessment.user_id == user.id)).all()
    return list(courses), list(sessions), list(assessments)


def topic_masteries(courses, sessions, assessments, now: datetime) -> dict[int, mastery_model.Mastery]:
    """Mastery for every topic the student has, keyed by topic id."""
    return {
        topic.id: mastery_model.estimate(_topic_evidence(course, topic.id, assessments, sessions), now)
        for course in courses
        for topic in course.topics
    }


def _risk_inputs(sessions: list[StudySession], assessments: list[Assessment], today: date):
    """Daily minutes from the first session to today, and score events as (day index, fraction)."""
    dated = [(as_utc(s.started_at).date(), s.minutes) for s in sessions if as_utc(s.started_at).date() <= today]
    if not dated:
        return np.zeros(0), []
    origin = min(d for d, _ in dated)
    daily = np.zeros((today - origin).days + 1)
    for d, minutes in dated:
        daily[(d - origin).days] += minutes
    scores = [
        ((as_utc(a.taken_at).date() - origin).days, min(a.score / a.max_score, 1.0))
        for a in assessments
        if a.max_score > 0 and as_utc(a.taken_at).date() <= today
    ]
    return daily, scores


def _save_snapshot(db: Session, user: User, kind: str, course_id: int | None, today: date, version: str,
                   value: dict, features: dict | None = None) -> None:
    existing = db.scalar(
        select(Prediction).where(
            Prediction.user_id == user.id,
            Prediction.kind == kind,
            Prediction.course_id == course_id if course_id is not None else Prediction.course_id.is_(None),
            Prediction.made_on == today,
        )
    )
    if existing:
        existing.model_version, existing.value, existing.features = version, value, features
    else:
        db.add(Prediction(user_id=user.id, kind=kind, course_id=course_id, made_on=today,
                          model_version=version, value=value, features=features))


def compute_insights(db: Session, user: User, now: datetime | None = None, pass_mark: float = 0.5) -> InsightsOut:
    now = now or datetime.now(UTC)
    today = now.date()
    courses, sessions, assessments = load_user_data(db, user)
    masteries = topic_masteries(courses, sessions, assessments, now)

    course_out = []
    for course in courses:
        topics_out, posteriors = [], []
        for topic in course.topics:
            m = masteries[topic.id]
            posteriors.append(TopicPosterior(topic.weight, m.a, m.b, m.evidence))
            topics_out.append(
                TopicInsight(
                    topic_id=topic.id,
                    name=topic.name,
                    weight=topic.weight,
                    mastery=MasteryOut(
                        mean=m.mean, lo=m.lo, hi=m.hi, evidence=m.evidence,
                        n_observations=m.n_observations, last_evidence_at=m.last_evidence_at,
                    ),
                )
            )
        perf = predict(posteriors, pass_mark=pass_mark, seed=course.id)
        note = None
        if not course.topics:
            note = "Add topics to this course to get an expected score."
        elif perf is None:
            note = "Log a few scores or confidence ratings and an expected score will appear."
        else:
            _save_snapshot(db, user, "performance", course.id, today, PERFORMANCE_VERSION, asdict(perf))
        course_out.append(
            CourseInsight(
                course_id=course.id,
                name=course.name,
                exam_date=course.exam_date,
                topics=topics_out,
                performance=PerformanceOut(**asdict(perf)) if perf else None,
                performance_note=note,
            )
        )

    daily, scores = _risk_inputs(sessions, assessments, today)
    risk = risk_model.assess(daily, scores)
    if risk.status == "ok":
        _save_snapshot(
            db, user, "risk", None, today, risk.model_version,
            {"probability": risk.probability, "level": risk.level}, risk.features,
        )
    db.commit()

    return InsightsOut(
        generated_at=now,
        courses=course_out,
        risk=RiskOut(
            status=risk.status,
            message=risk.message,
            probability=risk.probability,
            typical=risk.typical,
            level=risk.level,
            horizon_days=risk.horizon_days,
            drivers=[DriverOut(label=d.label, effect=d.effect, detail=d.detail) for d in risk.drivers],
            model_version=risk.model_version,
        ),
    )
