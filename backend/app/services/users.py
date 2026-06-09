from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserRow
from app.services.passwords import hash_password, verify_password


def get_user_by_email(session: Session, email: str) -> UserRow | None:
    normalized = email.strip().lower()
    return session.scalar(select(UserRow).where(UserRow.email == normalized))


def get_user_by_id(session: Session, user_id: int) -> UserRow | None:
    return session.get(UserRow, user_id)


def create_user(
    session: Session,
    *,
    email: str,
    password: str,
    display_name: str | None = None,
) -> UserRow:
    normalized = email.strip().lower()
    user = UserRow(
        email=normalized,
        password_hash=hash_password(password),
        display_name=(display_name or normalized.split("@", 1)[0]).strip()[:128],
        tier="free",
    )
    session.add(user)
    session.flush()
    return user


def authenticate_user(session: Session, *, email: str, password: str) -> UserRow | None:
    user = get_user_by_email(session, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def update_user_tier(session: Session, user_id: int, tier: str) -> UserRow | None:
    user = get_user_by_id(session, user_id)
    if user is None:
        return None
    user.tier = tier
    session.flush()
    return user
