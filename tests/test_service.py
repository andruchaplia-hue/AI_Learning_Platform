import pytest

from backend.use_cases.use_case_1_autocomplete.service import AutocompleteService
from backend.use_cases.use_case_1_autocomplete.utils import (
    parse_provider_exception,
    split_options,
)
from backend.domain.exceptions import ValidationError
from backend.infrastructure.config.settings import load_settings


@pytest.mark.asyncio
async def test_service_with_mock_provider():
    settings = load_settings()
    settings.provider = "mock"
    service = AutocompleteService(settings)

    response = await service.generate_autocomplete("Artificial Intelligence is")

    assert response.completion is not None
    assert len(response.completion) > 0
    assert response.execution_time_sec >= 0.0


@pytest.mark.asyncio
async def test_service_validation_error():
    settings = load_settings()
    settings.provider = "mock"
    service = AutocompleteService(settings)

    with pytest.raises(ValidationError):
        await service.generate_autocomplete("hi")


def test_split_options_bullets():
    text = "* Option A: text A\n* Option B: text B"
    opts = split_options(text)
    assert len(opts) == 2
    assert opts[0] == "text A"
    assert opts[1] == "text B"


def test_split_options_with_preamble():
    text = "Completion options:\n* Option A: text A\n* Option B: text B"
    opts = split_options(text)
    assert len(opts) == 2
    assert opts[0] == "text A"
    assert opts[1] == "text B"


def test_split_options_numbered():
    text = "1. ate a bagel.\n2. dropped her ring into a deep puddle."
    opts = split_options(text)
    assert len(opts) == 2
    assert opts[0] == "ate a bagel."
    assert opts[1] == "dropped her ring into a deep puddle."


def test_split_options_single():
    text = "This is a single block of text."
    opts = split_options(text)
    assert len(opts) == 1
    assert opts[0] == text


@pytest.mark.asyncio
async def test_service_modes():
    settings = load_settings()
    settings.provider = "mock"
    service = AutocompleteService(settings)

    # Test sentence mode (default)
    res_sentence = await service.generate_autocomplete(
        "Artificial Intelligence is", mode="sentence"
    )
    assert res_sentence.completions is not None
    assert len(res_sentence.completions) > 0

    # Test paragraph mode
    res_paragraph = await service.generate_autocomplete(
        "Artificial Intelligence is", mode="paragraph"
    )
    assert res_paragraph.completions is not None
    assert len(res_paragraph.completions) > 0


def test_parse_provider_exception():
    quota_err = Exception(
        "429 ResourceExhausted: Quota exceeded for aiplatform.googleapis.com"
    )
    assert "quota or rate limit" in parse_provider_exception(quota_err)

    auth_err = Exception("401 Unauthenticated: Invalid API key provided")
    assert "Authentication failed" in parse_provider_exception(auth_err)

    timeout_err = Exception("DeadlineExceeded: Request timed out")
    assert "timed out" in parse_provider_exception(timeout_err)

    unknown_err = Exception("Something went wrong")
    assert "AI provider service error" in parse_provider_exception(unknown_err)
