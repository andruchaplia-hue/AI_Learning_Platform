from typing import Any

from fastapi import APIRouter, Depends

from backend.infrastructure.auth.dependencies import get_current_user
from backend.infrastructure.config.settings import AppSettings, get_settings
from backend.use_cases.use_case_5_content_gen.auth_service import AuthService
from backend.use_cases.use_case_5_content_gen.models import (
    AuthTokenResponse,
    DevLoginRequest,
    DevUserItem,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def get_auth_service(settings: AppSettings = Depends(get_settings)) -> AuthService:
    """Dependency injector for AuthService."""
    return AuthService(settings)


@router.post("/register", response_model=AuthTokenResponse)
async def register(
    payload: UserRegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    """Register a new user account."""
    return await service.register_user(payload)


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    payload: UserLoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    """Authenticate and obtain JWT access token."""
    return await service.login_user(payload)


@router.get("/dev-users", response_model=list[DevUserItem])
async def list_dev_users(
    service: AuthService = Depends(get_auth_service),
) -> list[DevUserItem]:
    """List registered users for quick dev authentication."""
    users = await service.list_dev_users()
    return [DevUserItem(**u) for u in users]


@router.post("/dev-login", response_model=AuthTokenResponse)
async def dev_login(
    payload: DevLoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    """Quick dev login by username or email without requiring password."""
    return await service.dev_login(payload.identifier)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    """Get authenticated user info."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        created_at=current_user.get("created_at", ""),
    )
