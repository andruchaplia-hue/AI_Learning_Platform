from typing import Any

from fastapi import APIRouter, Depends

from backend.infrastructure.auth.dependencies import get_current_user
from backend.infrastructure.config.settings import AppSettings, get_settings
from backend.use_cases.use_case_5_content_gen.models import (
    UserProfileDTO,
    UserProfileUpdateRequest,
)
from backend.use_cases.use_case_5_content_gen.profile_service import ProfileService

router = APIRouter(prefix="/api/v1/profile", tags=["User Profile"])


def get_profile_service(settings: AppSettings = Depends(get_settings)) -> ProfileService:
    """Dependency injector for ProfileService."""
    return ProfileService(settings)


@router.get("", response_model=UserProfileDTO)
async def get_profile(
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileDTO:
    """Retrieve profile settings for current authenticated user."""
    return await service.get_profile(user_id=current_user["id"])


@router.put("", response_model=UserProfileDTO)
async def update_profile(
    payload: UserProfileUpdateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileDTO:
    """Update profile settings for current authenticated user."""
    return await service.update_profile(user_id=current_user["id"], req=payload)
