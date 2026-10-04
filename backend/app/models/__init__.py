import secrets
from datetime import UTC, datetime

from datetime import date

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_pseudonym() -> str:
    return secrets.token_hex(12)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # Random id used in the event log and aggregates, so analytics never carry the user id.
    pseudonym: Mapped[str] = mapped_column(String(24), unique=True, default=new_pseudonym)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    courses: Mapped[list["Course"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["StudySession"]] = relationship(cascade="all, delete-orphan")
    assessments: Mapped[list["Assessment"]] = relationship(cascade="all, delete-orphan")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), default="")
    institution: Mapped[str] = mapped_column(String(200), default="")
    degree: Mapped[str] = mapped_column(String(200), default="")
    year: Mapped[int | None] = mapped_column(Integer)
    goal_type: Mapped[str] = mapped_column(String(50), default="")  # exam | job | higher_studies | ...
    goal_text: Mapped[str] = mapped_column(Text, default="")
    weekly_study_hours: Mapped[float | None] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="profile")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    exam_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="courses")
    topics: Mapped[list["Topic"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # Relative importance of the topic in the exam; normalised when used.
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    course: Mapped[Course] = relationship(back_populates="topics")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    minutes: Mapped[int] = mapped_column(Integer)
    confidence_before: Mapped[int | None] = mapped_column(Integer)  # 1-5 self-rating
    confidence_after: Mapped[int | None] = mapped_column(Integer)  # 1-5 self-rating
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    # Removing a topic keeps the course-level score but drops the topic link.
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30), default="quiz")  # quiz | assignment | exam | mock
    score: Mapped[float] = mapped_column(Float)
    max_score: Mapped[float] = mapped_column(Float)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    """Append-only learning event log, keyed by pseudonym rather than user id."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    pseudonym: Mapped[str] = mapped_column(String(24), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Prediction(Base):
    """One stored model output per user, kind and course per day (the latest of the day wins).

    Kept so predictions can be compared with what actually happened later, which is how the models
    get evaluated on Padhotec's own students.
    """

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # "risk" | "performance"
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    made_on: Mapped[date] = mapped_column(Date)
    model_version: Mapped[str] = mapped_column(String(50))
    value: Mapped[dict] = mapped_column(JSON)
    features: Mapped[dict | None] = mapped_column(JSON)
