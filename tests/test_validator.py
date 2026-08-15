import pytest

from backend.domain.exceptions import ValidationError
from backend.domain.validators.text_validator import validate_input_text


def test_validate_input_text_success():
    text = "Artificial Intelligence is transforming world"
    result = validate_input_text(text, min_length=5, max_length=5000)
    assert result == text


def test_validate_input_text_too_short():
    with pytest.raises(ValidationError) as exc_info:
        validate_input_text("AI", min_length=5, max_length=5000)
    assert "too short" in str(exc_info.value)


def test_validate_input_text_empty():
    with pytest.raises(ValidationError) as exc_info:
        validate_input_text("   ", min_length=5, max_length=5000)
    assert "empty" in str(exc_info.value)


def test_validate_input_text_too_long():
    long_text = "a" * 5001
    with pytest.raises(ValidationError) as exc_info:
        validate_input_text(long_text, min_length=5, max_length=5000)
    assert "exceeds maximum length" in str(exc_info.value)
