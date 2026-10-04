from fastapi import APIRouter, status
from sqlalchemy import select

from app.deps import DB, CurrentUser, owned_course, owned_topic
from app.models import Course, Topic
from app.schemas import CourseIn, CourseOut, TopicIn, TopicOut
from app.services.events import COURSE_ADDED, record_event

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseOut])
def list_courses(user: CurrentUser, db: DB):
    return db.scalars(select(Course).where(Course.user_id == user.id).order_by(Course.id)).all()


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(body: CourseIn, user: CurrentUser, db: DB):
    course = Course(user_id=user.id, **body.model_dump())
    db.add(course)
    record_event(db, user, COURSE_ADDED, {"has_exam_date": body.exam_date is not None})
    db.commit()
    return course


@router.put("/{course_id}", response_model=CourseOut)
def update_course(course_id: int, body: CourseIn, user: CurrentUser, db: DB):
    course = owned_course(db, user, course_id)
    for field, value in body.model_dump().items():
        setattr(course, field, value)
    db.commit()
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, user: CurrentUser, db: DB):
    db.delete(owned_course(db, user, course_id))
    db.commit()


@router.post("/{course_id}/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(course_id: int, body: TopicIn, user: CurrentUser, db: DB):
    course = owned_course(db, user, course_id)
    topic = Topic(course_id=course.id, **body.model_dump())
    db.add(topic)
    db.commit()
    return topic


@router.put("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: int, body: TopicIn, user: CurrentUser, db: DB):
    topic = owned_topic(db, user, topic_id)
    for field, value in body.model_dump().items():
        setattr(topic, field, value)
    db.commit()
    return topic


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: int, user: CurrentUser, db: DB):
    db.delete(owned_topic(db, user, topic_id))
    db.commit()
