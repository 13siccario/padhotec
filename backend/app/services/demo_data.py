"""A synthetic demo cohort, for showing the app without real students.

Everything generated here is invented and every account is marked as a demo account. Demo data is kept out of
real students' peer groups and out of the evidence page. It proves nothing about the models: it only fills the
screens. The simulator uses its own learning and forgetting dynamics (slower forgetting than the app assumes), so
it is not the model run backwards.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    Course,
    DemoAccount,
    Event,
    StudentProfile,
    StudentSkill,
    StudySession,
    Topic,
    TopicSkill,
    User,
)
from app.security import hash_password
from app.services.events import ASSESSMENT_RECORDED, COURSE_ADDED, SESSION_LOGGED, record_event

DEMO_DOMAIN = "demo.padhotec.example.com"
DEMO_PASSWORD = "demo-password"
HISTORY_DAYS = 60

COURSES = {
    "Statistics": {"exam_in": 14, "topics": [("Bayes rule", 2.0), ("Hypothesis tests", 1.0), ("Regression", 1.0),
                                             ("Probability distributions", 1.0)]},
    "Algorithms": {"exam_in": 35, "topics": [("Graphs", 1.0), ("Sorting", 1.0), ("Dynamic programming", 2.0)]},
}
TOPIC_SKILL = {
    "Bayes rule": "probability", "Probability distributions": "probability", "Regression": "statistics",
    "Hypothesis tests": "statistics", "Graphs": "data_structures", "Dynamic programming": "data_structures",
}
ARCHETYPES = ["steady"] * 10 + ["improving"] * 5 + ["erratic"] * 4 + ["quiet"] * 4  # background cohort mix

NAMED = [  # (key, archetype, history days, courses, ability override)
    ("steady", "steady", HISTORY_DAYS, ["Statistics", "Algorithms"], None),
    ("quiet", "quiet", HISTORY_DAYS, ["Statistics"], 0.5),
    ("new", "new", 6, ["Statistics"], None),
]


@dataclass(frozen=True)
class Seeded:
    email: str
    archetype: str


def demo_email(key: str) -> str:
    return f"{key}@{DEMO_DOMAIN}"


def _active(rng, archetype: str, day_ago: int, was_active: bool) -> bool:
    if archetype == "steady":
        return rng.random() < 0.8
    if archetype == "improving":
        return rng.random() < 0.45 + 0.4 * (1 - day_ago / HISTORY_DAYS)
    if archetype == "erratic":
        return rng.random() < (0.75 if was_active else 0.3)  # streaks and gaps
    if archetype == "quiet":
        return day_ago > 21 and rng.random() < 0.8  # active, then silent for three weeks
    return rng.random() < 0.85  # "new"


def _simulate_student(rng, archetype: str, n_days: int, course_names: list[str], ability: float | None, now: datetime):
    """Sessions and assessments for one student, from a latent mastery per topic that rises with study and decays."""
    theta = ability if ability is not None else float(rng.beta(5, 3))
    topics = [(c, name, w) for c in course_names for name, w in COURSES[c]["topics"]]
    mastery = {name: float(np.clip(theta * rng.uniform(0.25, 0.85), 0.05, 0.9)) for _, name, _ in topics}
    sessions, assessments, quiz_n, was_active = [], [], 0, False
    for day_ago in range(n_days, 0, -1):  # up to yesterday, so a demo student has not already studied "today"
        mastery = {k: v * 0.996 for k, v in mastery.items()}  # forgetting, slower than the app assumes
        active = _active(rng, archetype, day_ago, was_active)
        was_active = active
        if not active:
            continue
        weights = np.array([(1.05 - mastery[name]) * w for _, name, w in topics])
        c, name, _ = topics[int(rng.choice(len(topics), p=weights / weights.sum()))]
        minutes = int(np.clip(rng.lognormal(np.log(40), 0.35), 10, 120) // 5 * 5)
        mastery[name] += (1 - mastery[name]) * 0.05 * (minutes / 40)
        when = now.replace(hour=int(rng.integers(7, 22)), minute=int(rng.integers(0, 60)), second=0, microsecond=0) - timedelta(days=day_ago)
        after = int(np.clip(round(1 + 4 * np.clip(mastery[name] + rng.normal(0, 0.12), 0, 1)), 1, 5))
        rated = rng.random() < 0.85
        sessions.append(dict(course=c, topic=name, minutes=minutes, at=when,
                             after=after if rated else None,
                             before=max(1, after - int(rng.choice([0, 1, 1, 2]))) if rated else None))
        if rng.random() < 1 / 11:
            quiz_n += 1
            p = float(np.clip(mastery[name] + rng.normal(0, 0.07), 0.03, 0.97))
            assessments.append(dict(course=c, topic=name, title=f"Quiz {quiz_n}", kind="quiz",
                                    score=int(rng.binomial(10, p)), max=10, at=when + timedelta(hours=1)))
        if day_ago == 19 and archetype in ("steady", "improving"):  # a course-wide mock a few weeks back
            mean_m = float(np.mean([mastery[n] for cc, n, _ in topics if cc == course_names[0]]))
            frac = float(np.clip(mean_m + rng.normal(0, 0.06), 0.05, 0.97))
            assessments.append(dict(course=course_names[0], topic=None, title="Mock exam", kind="mock",
                                    score=round(frac * 50), max=50, at=when + timedelta(hours=2)))
    return sessions, assessments


def delete_demo_accounts(db: Session) -> int:
    """Remove demo accounts and only demo accounts."""
    users = list(db.scalars(select(User).join(DemoAccount, DemoAccount.user_id == User.id)))
    for u in users:
        db.execute(delete(Event).where(Event.pseudonym == u.pseudonym))
        db.delete(u)
    db.commit()
    return len(users)


def has_demo_accounts(db: Session) -> bool:
    return db.scalar(select(DemoAccount.user_id).limit(1)) is not None


def seed_demo(db: Session, seed: int = 7, n_background: int = 23, reset: bool = False, now: datetime | None = None) -> list[Seeded]:
    """Create the demo cohort. Returns what was created, or nothing if demo accounts already exist."""
    now = now or datetime.now(UTC)
    if reset:
        delete_demo_accounts(db)
    elif has_demo_accounts(db):
        return []

    rng = np.random.default_rng(seed)
    password_hash = hash_password(DEMO_PASSWORD)  # hashed once; the same demo password for every account
    plan = list(NAMED)
    for i in range(1, n_background + 1):
        archetype = ARCHETYPES[(i - 1) % len(ARCHETYPES)]
        courses = ["Statistics"] + (["Algorithms"] if rng.random() < 0.55 else [])
        plan.append((f"s{i:02d}", archetype, HISTORY_DAYS, courses, None))

    created = []
    for index, (key, archetype, n_days, course_names, ability) in enumerate(plan):
        institution = "Demo University A" if index < 3 or rng.random() < 0.7 else "Demo University B"
        user = User(email=demo_email(key), password_hash=password_hash, consented_at=now)
        user.profile = StudentProfile(
            display_name=f"Demo {key.title()}", institution=institution,
            degree="BSc Data Science" if institution.endswith("A") else "BSc Mathematics",
            goal_type="exam", goal_text="", weekly_study_hours=float(rng.choice([6, 8, 10])),
        )
        user.demo_link = DemoAccount()
        db.add(user)
        db.flush()

        course_rows, topic_rows = {}, {}
        for cname in course_names:
            cfg = COURSES[cname]
            course = Course(user_id=user.id, name=cname, exam_date=now + timedelta(days=cfg["exam_in"]))
            db.add(course)
            db.flush()
            course_rows[cname] = course
            for tname, weight in cfg["topics"]:
                topic = Topic(course_id=course.id, name=tname, weight=weight)
                db.add(topic)
                db.flush()
                topic_rows[tname] = topic
                if tname in TOPIC_SKILL and (key in ("steady", "quiet", "new") or rng.random() < 0.4):
                    db.add(TopicSkill(topic_id=topic.id, skill_key=TOPIC_SKILL[tname]))
            record_event(db, user, COURSE_ADDED, {"has_exam_date": True})

        sessions, assessments = _simulate_student(rng, archetype, n_days, course_names, ability, now)
        for s in sessions:
            db.add(StudySession(user_id=user.id, topic_id=topic_rows[s["topic"]].id, minutes=s["minutes"],
                                confidence_before=s["before"], confidence_after=s["after"], started_at=s["at"]))
            record_event(db, user, SESSION_LOGGED, {"topic_id": topic_rows[s["topic"]].id, "minutes": s["minutes"]}, ts=s["at"])
        for a in assessments:
            topic = topic_rows[a["topic"]] if a["topic"] else None
            db.add(Assessment(user_id=user.id, course_id=course_rows[a["course"]].id, topic_id=topic.id if topic else None,
                              title=a["title"], kind=a["kind"], score=a["score"], max_score=a["max"], taken_at=a["at"]))
            record_event(db, user, ASSESSMENT_RECORDED, {"kind": a["kind"], "fraction": a["score"] / a["max"]}, ts=a["at"])

        ratings = {"probability": 4, "statistics": 4, "programming": 5} if key == "steady" else (
            {"probability": int(rng.integers(2, 5)), "statistics": int(rng.integers(2, 5))} if rng.random() < 0.6 else {})
        for skill, rating in ratings.items():
            db.add(StudentSkill(user_id=user.id, skill_key=skill, rating=rating))
        created.append(Seeded(user.email, archetype))
    db.commit()
    return created
