from typing import Any

from fastapi import APIRouter, Depends, status

from backend.infrastructure.config.settings import AppSettings, get_settings
from backend.use_cases.use_case_4_code_generation.models import (
    AddDatasetEntryRequest,
    CodeGenerationRequest,
    CodeGenerationResponse,
    DatasetListResponse,
    FineTuneJobResponse,
)
from backend.use_cases.use_case_4_code_generation.service import CodeGenerationService

router = APIRouter(prefix="/api/v1/code-generation", tags=["Code Generation Assistant"])


def get_service(settings: AppSettings = Depends(get_settings)) -> CodeGenerationService:
    """Dependency injection helper for CodeGenerationService."""
    return CodeGenerationService(settings)


@router.post("", response_model=CodeGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_code(
    request: CodeGenerationRequest,
    service: CodeGenerationService = Depends(get_service),
) -> CodeGenerationResponse:
    """Generate code snippet or execute refactor using Semantic Kernel Agent pipeline."""
    return await service.generate_code(request)

@router.get("/dataset", response_model=DatasetListResponse, status_code=status.HTTP_200_OK)
async def get_dataset(
    service: CodeGenerationService = Depends(get_service),
) -> DatasetListResponse:
    """Retrieve fine-tuning dataset entries for dataset manager UI."""
    return service.get_dataset()


@router.post("/dataset", status_code=status.HTTP_201_CREATED)
async def add_dataset_entry(
    request: AddDatasetEntryRequest,
    service: CodeGenerationService = Depends(get_service),
) -> dict[str, Any]:
    """Add a new training pair example to the fine-tuning JSONL dataset."""
    return service.add_dataset_entry(request)


@router.post("/fine-tune", response_model=FineTuneJobResponse, status_code=status.HTTP_200_OK)
async def trigger_fine_tuning(
    service: CodeGenerationService = Depends(get_service),
) -> FineTuneJobResponse:
    """Retrieve fine-tuning job status and dataset readiness metrics."""
    return service.trigger_fine_tune_job()
