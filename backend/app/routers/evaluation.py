from fastapi import APIRouter

from app.deps import DB
from app.services.evaluation import build_evaluation

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("")
def get_evaluation(db: DB):
    """How accurate the models are. Public on purpose: it holds only aggregate figures and no student data."""
    return build_evaluation(db)
