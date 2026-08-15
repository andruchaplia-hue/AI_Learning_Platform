from typing import Any
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.domain.exceptions import AuthenticationError
from backend.infrastructure.auth.jwt_manager import JWTManager
from backend.infrastructure.auth.user_repository import UserRepository
from backend.infrastructure.config.settings import AppSettings, get_settings

security = HTTPBearer(auto_error=False)


def get_jwt_manager(settings: AppSettings = Depends(get_settings)) -> JWTManager:
    return JWTManager(settings)


def get_user_repository(settings: AppSettings = Depends(get_settings)) -> UserRepository:
    return UserRepository(db_path=settings.faq_memory_db_path)


async def get_current_user(
    auth_header: HTTPAuthorizationCredentials | None = Depends(security),
    authorization: str | None = Header(default=None),
    jwt_manager: JWTManager = Depends(get_jwt_manager),
    user_repo: UserRepository = Depends(get_user_repository),
) -> dict[str, Any]:
    """FastAPI security dependency to extract and validate authenticated user from JWT Bearer token.

    Raises:
        AuthenticationError: If token is missing, invalid or user does not exist.
    """
    token = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise AuthenticationError("Could not validate credentials: Missing Bearer token")

    payload = jwt_manager.decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Could not validate credentials: Missing subject in token")

    user = user_repo.get_user_by_id(str(user_id))
    if not user:
        raise AuthenticationError("Could not validate credentials: User not found")

    return user
