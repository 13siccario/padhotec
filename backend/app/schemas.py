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
