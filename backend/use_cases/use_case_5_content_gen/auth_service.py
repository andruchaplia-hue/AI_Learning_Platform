import logging
from typing import Any

from backend.domain.exceptions import AuthenticationError, ValidationError
from backend.infrastructure.auth.jwt_manager import JWTManager
from backend.infrastructure.auth.password_hasher import PasswordHasher
from backend.infrastructure.auth.user_repository import UserRepository
from backend.infrastructure.config.settings import AppSettings
from backend.use_cases.use_case_5_content_gen.models import (
    AuthTokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Domain service responsible for user registration, authentication, and JWT token issuance."""

    def __init__(
        self,
        settings: AppSettings,
        user_repo: UserRepository | None = None,
        jwt_manager: JWTManager | None = None,
    ) -> None:
        self.user_repo = user_repo or UserRepository(db_path=settings.faq_memory_db_path)
        self.jwt_manager = jwt_manager or JWTManager(settings)

    def _issue_token(self, user: dict[str, Any]) -> AuthTokenResponse:
        """Create JWT token and wrap in AuthTokenResponse DTO."""
        token = self.jwt_manager.create_access_token(
            data={"sub": user["id"], "username": user["username"], "email": user["email"]}
        )
        return AuthTokenResponse(
            access_token=token,
            user_id=user["id"],
            username=user["username"],
            email=user["email"],
        )

    async def register_user(self, req: UserRegisterRequest) -> AuthTokenResponse:
        """Register a new user account and generate an initial JWT token."""
        if not req.username or len(req.username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
        if not req.password or len(req.password) < 6:
            raise ValidationError("Password must be at least 6 characters long")

        password_hash = PasswordHasher.hash_password(req.password)
        user = self.user_repo.create_user(
            username=req.username, email=req.email, password_hash=password_hash
        )
        return self._issue_token(user)

    async def login_user(self, req: UserLoginRequest) -> AuthTokenResponse:
        """Authenticate user credentials and return JWT access token."""
        user = self.user_repo.get_user_by_email(req.email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not PasswordHasher.verify_password(req.password, user["password_hash"]):
            raise AuthenticationError("Invalid email or password")

        return self._issue_token(user)

    async def list_dev_users(self) -> list[dict[str, Any]]:
        """List registered users for quick dev authentication."""
        return self.user_repo.list_all_users()

    async def dev_login(self, identifier: str) -> AuthTokenResponse:
        """Issue JWT token directly for existing user without password requirement."""
        clean_id = identifier.strip().lower()
        user = (
            self.user_repo.get_user_by_email(clean_id)
            or self.user_repo.get_user_by_username(clean_id)
            or self.user_repo.get_user_by_id(clean_id)
        )
        if not user:
            raise AuthenticationError(f"User '{identifier}' not found in database")

        return self._issue_token(user)
