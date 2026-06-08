import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps.auth import get_current_user
from app.config import Settings, get_settings
from app.db.session import session_scope
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.services.auth_tokens import create_access_token
from app.services.users import authenticate_user, create_user, get_user_by_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


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


def _issue_token(user, settings: Settings) -> TokenResponse:
    token = create_access_token(user_id=user.id, settings=settings)
    return TokenResponse(access_token=token, user=_to_public_user(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    database_url = _require_database(settings)

    with session_scope(database_url) as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible.",
            )

        if get_user_by_email(session, body.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una cuenta con ese correo.",
            )

        try:
            user = create_user(
                session,
                email=body.email,
                password=body.password,
                display_name=body.display_name,
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una cuenta con ese correo.",
            ) from None

        logger.info("Usuario registrado id=%s email=%s", user.id, user.email)
        return _issue_token(user, settings)


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    database_url = _require_database(settings)

    with session_scope(database_url) as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible.",
            )

        user = authenticate_user(session, email=body.email, password=body.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos.",
            )

        logger.info("Login exitoso id=%s", user.id)
        return _issue_token(user, settings)


@router.get("/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user
