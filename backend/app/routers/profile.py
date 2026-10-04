from fastapi import APIRouter

from app.deps import DB, CurrentUser
from app.models import StudentProfile
from app.schemas import ProfileIn, ProfileOut
from app.services.events import GOAL_SET, record_event

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(user: CurrentUser):
    return user.profile


@router.put("", response_model=ProfileOut)
def update_profile(body: ProfileIn, user: CurrentUser, db: DB):
    profile = user.profile or StudentProfile(user_id=user.id)
    goal_changed = (profile.goal_type, profile.goal_text) != (body.goal_type, body.goal_text)
    for field, value in body.model_dump().items():
        setattr(profile, field, value)
    db.add(profile)
    if goal_changed and body.goal_type:
        # The goal type is a controlled value; free-text goal stays out of the event log.
        record_event(db, user, GOAL_SET, {"goal_type": body.goal_type})
    db.commit()
    return profile
