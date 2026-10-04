from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Course, Topic, User
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def current_user(
    db: DB,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    user_id = decode_access_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def owned_course(db: Session, user: User, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    return course


def owned_topic(db: Session, user: User, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None or topic.course.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")
    return topic
