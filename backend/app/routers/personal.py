from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import DB, CurrentUser
from app.models import PrivacySetting, StudentSkill
from app.schemas import CareersOut, PeerOut, PlanOut, PrivacyIO, SkillOut, SkillRatingIn
from app.services import personal
from app.services.careers import skills_by_key

router = APIRouter(tags=["personal"])


@router.get("/plan", response_model=PlanOut)
def get_plan(
    user: CurrentUser,
    db: DB,
    minutes: Annotated[int | None, Query(ge=15, le=240)] = None,
    utc_offset_minutes: Annotated[int, Query(ge=-840, le=840)] = 0,
):
    """Today's study plan. `minutes` overrides the daily budget; the offset is the browser's local time zone."""
    return personal.compute_plan(db, user, minutes=minutes, utc_offset_minutes=utc_offset_minutes)


@router.get("/skills", response_model=list[SkillOut])
def list_skills(user: CurrentUser, db: DB):
    return personal.compute_skills(db, user)


@router.put("/skills/{key}", response_model=list[SkillOut])
def rate_skill(key: str, body: SkillRatingIn, user: CurrentUser, db: DB):
    if key not in skills_by_key():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown skill")
    row = db.get(StudentSkill, (user.id, key))
    if body.rating is None:
        if row:
            db.delete(row)
    elif row:
        row.rating = body.rating
    else:
        db.add(StudentSkill(user_id=user.id, skill_key=key, rating=body.rating))
    db.commit()
    return personal.compute_skills(db, user)


@router.get("/careers", response_model=CareersOut)
def get_careers(user: CurrentUser, db: DB):
    return personal.compute_careers(db, user)


@router.get("/peers", response_model=PeerOut)
def get_peers(user: CurrentUser, db: DB):
    return personal.compute_peers(db, user)


@router.get("/privacy", response_model=PrivacyIO)
def get_privacy(user: CurrentUser, db: DB):
    return PrivacyIO(peer_stats_opt_out=personal.is_opted_out(db, user.id))


@router.put("/privacy", response_model=PrivacyIO)
def set_privacy(body: PrivacyIO, user: CurrentUser, db: DB):
    row = db.get(PrivacySetting, user.id)
    if row:
        row.peer_stats_opt_out = body.peer_stats_opt_out
    else:
        db.add(PrivacySetting(user_id=user.id, peer_stats_opt_out=body.peer_stats_opt_out))
    db.commit()
    return body
