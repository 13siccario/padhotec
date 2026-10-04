from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import DB, CurrentUser, owned_course, owned_topic
from app.models import Assessment, StudySession
from app.schemas import AssessmentIn, AssessmentOut, SessionIn, SessionOut
from app.services.events import ASSESSMENT_RECORDED, SESSION_LOGGED, record_event

router = APIRouter(tags=["logs"])


@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def log_session(body: SessionIn, user: CurrentUser, db: DB):
    topic = owned_topic(db, user, body.topic_id)
    data = body.model_dump(exclude_none=True)
    session = StudySession(user_id=user.id, **data)
    db.add(session)
    db.flush()
    record_event(
        db,
        user,
        SESSION_LOGGED,
        {
            "topic_id": topic.id,
            "minutes": session.minutes,
            "confidence_before": session.confidence_before,
            "confidence_after": session.confidence_after,
        },
        ts=session.started_at,
    )
    db.commit()
    return session


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(user: CurrentUser, db: DB, topic_id: int | None = None):
    query = select(StudySession).where(StudySession.user_id == user.id)
    if topic_id is not None:
        query = query.where(StudySession.topic_id == topic_id)
    return db.scalars(query.order_by(StudySession.started_at.desc())).all()


@router.post("/assessments", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def record_assessment(body: AssessmentIn, user: CurrentUser, db: DB):
    course = owned_course(db, user, body.course_id)
    if body.score > body.max_score:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "score cannot exceed max_score")
    if body.topic_id is not None:
        topic = owned_topic(db, user, body.topic_id)
        if topic.course_id != course.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "topic does not belong to course")
    assessment = Assessment(user_id=user.id, **body.model_dump(exclude_none=True))
    db.add(assessment)
    db.flush()
    record_event(
        db,
        user,
        ASSESSMENT_RECORDED,
        {
            "course_id": course.id,
            "topic_id": assessment.topic_id,
            "kind": assessment.kind,
            "fraction": assessment.score / assessment.max_score,
        },
        ts=assessment.taken_at,
    )
    db.commit()
    return assessment


@router.get("/assessments", response_model=list[AssessmentOut])
def list_assessments(user: CurrentUser, db: DB, course_id: int | None = None):
    query = select(Assessment).where(Assessment.user_id == user.id)
    if course_id is not None:
        query = query.where(Assessment.course_id == course_id)
    return db.scalars(query.order_by(Assessment.taken_at.desc())).all()
