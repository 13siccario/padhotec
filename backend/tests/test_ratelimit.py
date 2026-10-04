import pytest
from fastapi import HTTPException

from app.ratelimit import AttemptLimiter
from tests.conftest import register


def test_limiter_blocks_then_recovers_after_window():
    now = [0.0]
    limiter = AttemptLimiter(max_attempts=2, window_seconds=10, clock=lambda: now[0])
    limiter.record("k")
    limiter.record("k")
    with pytest.raises(HTTPException) as exc:
        limiter.check("k")
    assert exc.value.status_code == 429 and int(exc.value.headers["Retry-After"]) == 10
    now[0] = 10.1
    limiter.check("k")  # window has passed


def test_login_locks_after_repeated_failures_and_reports_retry_after(client):
    register(client)
    bad = {"email": "a@example.com", "password": "wrong-password"}
    assert [client.post("/auth/login", json=bad).status_code for _ in range(5)] == [401] * 5
    locked = client.post("/auth/login", json=bad)
    assert locked.status_code == 429 and "retry-after" in locked.headers
    # Even the correct password is refused while locked, so guessing gains nothing.
    good = {"email": "a@example.com", "password": "correct-horse"}
    assert client.post("/auth/login", json=good).status_code == 429


def test_successful_login_resets_the_account_counter(client):
    register(client)
    bad = {"email": "a@example.com", "password": "wrong-password"}
    good = {"email": "a@example.com", "password": "correct-horse"}
    for _ in range(4):
        client.post("/auth/login", json=bad)
    assert client.post("/auth/login", json=good).status_code == 200
    for _ in range(4):
        assert client.post("/auth/login", json=bad).status_code == 401


def test_rotating_emails_hits_the_per_ip_limit(client):
    codes = [
        client.post("/auth/login", json={"email": f"u{i}@example.com", "password": "wrong-password"}).status_code
        for i in range(22)
    ]
    assert codes[:20] == [401] * 20 and codes[20:] == [429, 429]


def test_registration_is_limited_per_ip(client):
    codes = [
        client.post(
            "/auth/register", json={"email": f"n{i}@example.com", "password": "longenough1", "consent": True}
        ).status_code
        for i in range(12)
    ]
    assert codes[:10] == [201] * 10 and codes[10:] == [429, 429]
