from typing import Any
from fastapi import APIRouter, Depends, Response

from backend.infrastructure.auth.dependencies import get_current_user
from backend.infrastructure.config.settings import AppSettings, get_settings
from backend.use_cases.use_case_5_content_gen.dataset_service import PersonalizationDatasetService
from backend.use_cases.use_case_5_content_gen.models import (
    WritingSampleCreateRequest,
    WritingSampleListResponse,
    WritingSampleResponse,
)
from backend.use_cases.use_case_5_content_gen.service import ContentGenerationService

router = APIRouter(
    prefix="/api/v1/content-generation/examples",
    tags=["Personalization Dataset"],
)


def get_dataset_service(
    settings: AppSettings = Depends(get_settings),
) -> PersonalizationDatasetService:
    service = ContentGenerationService(settings)
    return service.dataset_service


@router.get("", response_model=WritingSampleListResponse)
async def list_examples(
    current_user: dict[str, Any] = Depends(get_current_user),
    dataset_service: PersonalizationDatasetService = Depends(get_dataset_service),
) -> WritingSampleListResponse:
    """List all personal writing samples for current user."""
    samples = dataset_service.list_writing_samples(user_id=current_user["id"])
    return WritingSampleListResponse(
        samples=[WritingSampleResponse(**s) for s in samples],
        total_count=len(samples),
    )


@router.post("", response_model=WritingSampleResponse)
async def create_example(
    payload: WritingSampleCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    dataset_service: PersonalizationDatasetService = Depends(get_dataset_service),
) -> WritingSampleResponse:
    """Create a new writing sample and index it into ChromaDB for few-shot personalization."""
    sample = dataset_service.add_writing_sample(
        user_id=current_user["id"],
        title=payload.title,
        content_type=payload.content_type,
        content=payload.content,
        tags=payload.tags,
    )
    return WritingSampleResponse(**sample)


@router.delete("/{sample_id}")
async def delete_example(
    sample_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    dataset_service: PersonalizationDatasetService = Depends(get_dataset_service),
) -> dict[str, Any]:
    """Delete writing sample by ID."""
    deleted = dataset_service.delete_writing_sample(
        sample_id=sample_id, user_id=current_user["id"]
    )
    return {"status": "success", "deleted": deleted}


@router.get("/export/jsonl")
async def export_dataset(
    current_user: dict[str, Any] = Depends(get_current_user),
    dataset_service: PersonalizationDatasetService = Depends(get_dataset_service),
) -> Response:
    """Export user writing samples and high-rated generations as JSONL dataset for model fine-tuning."""
    jsonl_data = dataset_service.export_dataset_jsonl(user_id=current_user["id"])
    return Response(
        content=jsonl_data,
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f"attachment; filename=personalization_{current_user['username']}_dataset.jsonl"
        },
    )
