from typing import Any
from fastapi import APIRouter, Depends

from backend.infrastructure.auth.dependencies import get_current_user
from backend.infrastructure.config.settings import AppSettings, get_settings
from backend.use_cases.use_case_5_content_gen.models import (
    ContentFeedbackRequest,
    ContentGenerationRequest,
    ContentGenerationResponse,
    ContentHistoryItem,
    ContentSubmitRequest,
)
from backend.use_cases.use_case_5_content_gen.service import ContentGenerationService

router = APIRouter(
    prefix="/api/v1/content-generation", tags=["Personalized Content Generator"]
)


def get_content_service(settings: AppSettings = Depends(get_settings)) -> ContentGenerationService:
    return ContentGenerationService(settings)


@router.post("", response_model=ContentGenerationResponse)
async def generate_content(
    payload: ContentGenerationRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ContentGenerationService = Depends(get_content_service),
) -> ContentGenerationResponse:
    """Generate personalized content tailored to user profile and few-shot examples."""
    return await service.generate_content(user_id=current_user["id"], req=payload)


@router.post("/submit", response_model=ContentHistoryItem)
async def submit_post(
    payload: ContentSubmitRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ContentGenerationService = Depends(get_content_service),
) -> ContentHistoryItem:
    """Persist and publish a finalized post to the author's wall."""
    return await service.submit_post(user_id=current_user["id"], req=payload)


@router.get("/history", response_model=list[ContentHistoryItem])
async def get_history(
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ContentGenerationService = Depends(get_content_service),
) -> list[ContentHistoryItem]:
    """Retrieve content generation history for authenticated user."""
    return await service.get_history(user_id=current_user["id"])


@router.post("/feedback")
async def submit_feedback(
    payload: ContentFeedbackRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ContentGenerationService = Depends(get_content_service),
) -> dict[str, Any]:
    """Rate generated content and optionally save it to personalization dataset."""
    result = await service.submit_feedback(user_id=current_user["id"], req=payload)
    return {"status": "success", "data": result}
