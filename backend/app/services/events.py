from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Event, User

# Event types, a subset of the plan's learning event vocabulary.
SESSION_LOGGED = "SESSION_LOGGED"
ASSESSMENT_RECORDED = "ASSESSMENT_RECORDED"
COURSE_ADDED = "COURSE_ADDED"
GOAL_SET = "GOAL_SET"


def record_event(db: Session, user: User, type_: str, payload: dict, ts: datetime | None = None) -> Event:
    """Append to the event log under the user's pseudonym. Payloads must not hold free text or PII."""
    event = Event(pseudonym=user.pseudonym, type=type_, payload=payload)
    if ts is not None:
        event.ts = ts
    db.add(event)
    return event
