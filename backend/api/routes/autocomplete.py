from fastapi import APIRouter, Depends, Request, status

from backend.use_cases.use_case_1_autocomplete.models import (
    AutocompleteRequest,
    AutocompleteResponse,
)
from backend.use_cases.use_case_1_autocomplete.service import AutocompleteService

router = APIRouter(prefix="/api/v1/autocomplete", tags=["Text Autocomplete"])


def get_autocomplete_service(request: Request) -> AutocompleteService:
    """Dependency injector: reads AutocompleteService singleton from app.state."""
    return request.app.state.autocomplete_service


@router.post(
    "",
    response_model=AutocompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate text autocompletion",
    description="Accepts input text prompt and generates completion using LangChain LCEL pipeline",
)
async def generate_autocomplete(
    request: AutocompleteRequest,
    service: AutocompleteService = Depends(get_autocomplete_service),
) -> AutocompleteResponse:
    return await service.generate_autocomplete(raw_text=request.text, mode=request.mode)
