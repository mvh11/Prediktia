from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.db.session import session_scope
from app.schemas.auth import UserPublic
from app.services.auth_tokens import decode_access_token
from app.services.users import get_user_by_id

_bearer = HTTPBearer(auto_error=False)


def _require_database(settings: Settings) -> str:
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autenticación requiere DATABASE_URL (PostgreSQL).",
        )
    return settings.database_url


def _to_public_user(user) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        tier=user.tier,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> UserPublic:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(credentials.credentials, settings)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    database_url = _require_database(settings)
    with session_scope(database_url) as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible.",
            )
        user = get_user_by_id(session, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return _to_public_user(user)


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> UserPublic | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None

    user_id = decode_access_token(credentials.credentials, settings)
    if user_id is None or not settings.database_url:
        return None

    try:
        with session_scope(settings.database_url) as session:
            if session is None:
                return None
            user = get_user_by_id(session, user_id)
            if user is None:
                return None
            return _to_public_user(user)
    except Exception:
        return None
