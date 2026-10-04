from typing import Annotated

from fastapi import APIRouter, Query

from app.deps import DB, CurrentUser
from app.schemas import InsightsOut
from app.services.insights import compute_insights

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=InsightsOut)
def get_insights(user: CurrentUser, db: DB, pass_mark: Annotated[float, Query(gt=0, le=1)] = 0.5):
    """Mastery per topic, expected score per course, and an engagement-risk estimate for the signed-in student."""
    return compute_insights(db, user, pass_mark=pass_mark)
