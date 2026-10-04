from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import delete, select

from app.deps import DB, CurrentUser
from app.models import Event, StudentProfile, User, utcnow
from app.ratelimit import login_by_account, login_by_ip, register_by_ip
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    # Behind a reverse proxy this is the proxy's address; configure forwarded headers before deploying.
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, db: DB):
    ip = _client_ip(request)
    register_by_ip.check(ip)
    register_by_ip.record(ip)
    if not body.consent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Consent is required to create an account")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=email, password_hash=hash_password(body.password), consented_at=utcnow())
    user.profile = StudentProfile()
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: DB):
    ip = _client_ip(request)
    email = body.email.lower()
    account_key = f"{ip}|{email}"
    login_by_ip.check(ip)
    login_by_account.check(account_key)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(body.password, user.password_hash):
        login_by_ip.record(ip)
        login_by_account.record(account_key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    login_by_account.reset(account_key)
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_data(user: CurrentUser, db: DB):
    """Delete the account and everything derived from it, including pseudonymous events."""
    db.execute(delete(Event).where(Event.pseudonym == user.pseudonym))
    db.delete(user)
    db.commit()
