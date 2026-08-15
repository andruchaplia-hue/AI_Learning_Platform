import pytest
from backend.infrastructure.config.settings import load_settings
from backend.use_cases.use_case_1_autocomplete.models import (
    AutocompleteRequest,
    AutocompleteResponse,
)
from backend.use_cases.use_case_1_autocomplete.service import AutocompleteService


@pytest.mark.asyncio
async def test_use_case_1_isolated_service():
    settings = load_settings()
    settings.provider = "mock"
    service = AutocompleteService(settings)

    request = AutocompleteRequest(text="Artificial Intelligence is", mode="sentence")
    response = await service.generate_autocomplete(request.text, mode=request.mode)

    assert isinstance(response, AutocompleteResponse)
    assert response.completion is not None
    assert len(response.completions) > 0
    assert response.execution_time_sec >= 0.0
