from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    consent: bool


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    email: EmailStr
    consented_at: datetime | None
    is_demo: bool = False


class ProfileIn(BaseModel):
    display_name: str = Field(default="", max_length=100)
    institution: str = Field(default="", max_length=200)
    degree: str = Field(default="", max_length=200)
    year: int | None = Field(default=None, ge=1, le=10)
    goal_type: str = Field(default="", max_length=50)
    goal_text: str = Field(default="", max_length=2000)
    weekly_study_hours: float | None = Field(default=None, ge=0, le=100)


class ProfileOut(ProfileIn, ORM):
    pass


class TopicIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    weight: float = Field(default=1.0, gt=0, le=100)


class TopicOut(TopicIn, ORM):
    id: int
    course_id: int
    skill_key: str | None = None


class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    exam_date: datetime | None = None


class CourseOut(CourseIn, ORM):
    id: int
    topics: list[TopicOut] = []


class SessionIn(BaseModel):
    topic_id: int
    minutes: int = Field(gt=0, le=720)
    confidence_before: int | None = Field(default=None, ge=1, le=5)
    confidence_after: int | None = Field(default=None, ge=1, le=5)
    started_at: datetime | None = None


class SessionOut(SessionIn, ORM):
    id: int
    started_at: datetime


class AssessmentIn(BaseModel):
    course_id: int
    topic_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    kind: str = Field(default="quiz", pattern="^(quiz|assignment|exam|mock)$")
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    taken_at: datetime | None = None


class AssessmentOut(AssessmentIn, ORM):
    id: int
    taken_at: datetime


class MasteryOut(BaseModel):
    mean: float
    lo: float
    hi: float
    evidence: float
    n_observations: int
    last_evidence_at: datetime | None


class TopicInsight(BaseModel):
    topic_id: int
    name: str
    weight: float
    mastery: MasteryOut


class PerformanceOut(BaseModel):
    mean: float
    lo: float
    hi: float
    p_pass: float
    pass_mark: float
    covered_weight: float


class CourseInsight(BaseModel):
    course_id: int
    name: str
    exam_date: datetime | None
    topics: list[TopicInsight]
    performance: PerformanceOut | None
    performance_note: str | None = None


class DriverOut(BaseModel):
    label: str
    effect: str
    detail: str


class RiskOut(BaseModel):
    status: str
    message: str | None = None
    probability: float | None = None
    typical: float | None = None
    level: str | None = None
    horizon_days: int
    drivers: list[DriverOut] = []
    model_version: str | None = None


class InsightsOut(BaseModel):
    generated_at: datetime
    courses: list[CourseInsight]
    risk: RiskOut


class PlanBlockOut(BaseModel):
    topic_id: int
    topic_name: str
    course_id: int
    course_name: str
    minutes: int
    kind: str
    reason: str


class PlanOut(BaseModel):
    budget_minutes: int
    studied_today: int
    remaining: int
    headline: str
    note: str
    blocks: list[PlanBlockOut]


class SkillRatingIn(BaseModel):
    rating: int | None = Field(ge=1, le=5)


class TopicSkillIn(BaseModel):
    skill_key: str | None = Field(default=None, max_length=50)


class SkillLevelOut(BaseModel):
    mean: float
    lo: float
    hi: float


class SkillOut(BaseModel):
    key: str
    label: str
    rating: int | None
    level: SkillLevelOut | None
    topics: list[str]


class GapOut(BaseModel):
    skill: str
    label: str
    required: float
    current: float | None
    importance: int


class RoadmapStepOut(BaseModel):
    skill: str
    label: str
    current: float | None
    target: float
    reason: str
    your_topics: list[str]


class CareerOut(BaseModel):
    key: str
    label: str
    summary: str
    readiness_mean: float
    readiness_lo: float
    readiness_hi: float
    unrated: int
    total: int
    gaps: list[GapOut]
    roadmap: list[RoadmapStepOut]


class CareersOut(BaseModel):
    note: str
    rated_skills: int
    total_skills: int
    careers: list[CareerOut]


class PeerMetricOut(BaseModel):
    key: str
    label: str
    unit: str
    you: float | None
    p25: float
    median: float
    p75: float
    position: str | None


class TopicSuggestionOut(BaseModel):
    course: str
    topic: str
    peers_tracking: int
    cohort_size: int


class PeerOut(BaseModel):
    status: str
    level: str | None = None
    label: str | None = None
    cohort_size: int | None = None
    metrics: list[PeerMetricOut] = []
    common_topics: list[TopicSuggestionOut] = []
    note: str | None = None


class PrivacyIO(BaseModel):
    peer_stats_opt_out: bool
