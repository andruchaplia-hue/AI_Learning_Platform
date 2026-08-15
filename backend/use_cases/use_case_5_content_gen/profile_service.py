import logging

from backend.domain.exceptions import ValidationError
from backend.infrastructure.auth.user_repository import UserRepository
from backend.infrastructure.config.settings import AppSettings
from backend.use_cases.use_case_5_content_gen.models import (
    UserProfileDTO,
    UserProfileUpdateRequest,
)

logger = logging.getLogger(__name__)


class ProfileService:
    """Domain service responsible for reading and updating user profile settings."""

    def __init__(
        self,
        settings: AppSettings,
        user_repo: UserRepository | None = None,
    ) -> None:
        self.user_repo = user_repo or UserRepository(db_path=settings.faq_memory_db_path)

    async def get_profile(self, user_id: str) -> UserProfileDTO:
        """Retrieve user profile by user ID.

        Raises:
            ValidationError: If user profile is not found.
        """
        profile = self.user_repo.get_user_profile(user_id)
        if not profile:
            raise ValidationError("User profile not found")
        return UserProfileDTO(**profile)

    async def update_profile(self, user_id: str, req: UserProfileUpdateRequest) -> UserProfileDTO:
        """Update profile settings and return the updated DTO."""
        profile_data = req.model_dump()
        updated = self.user_repo.update_user_profile(user_id, profile_data)
        return UserProfileDTO(**updated)
