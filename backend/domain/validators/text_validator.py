from backend.domain.exceptions import ValidationError


def validate_input_text(text: str, min_length: int = 5, max_length: int = 5000) -> str:
    """Validate user input text according to domain constraints.

    Args:
        text: Raw input text from user.
        min_length: Minimum allowed character count after stripping whitespace.
        max_length: Maximum allowed character count.

    Returns:
        Cleaned input text.

    Raises:
        ValidationError: If input fails validation rules.
    """
    if text is None:
        raise ValidationError("Input text cannot be null.")

    stripped_text = text.strip()
    if not stripped_text:
        raise ValidationError("Input text cannot be empty or contain only whitespace.")

    if len(stripped_text) < min_length:
        raise ValidationError(
            f"Input text is too short ({len(stripped_text)} characters). "
            f"Minimum required length is {min_length} characters."
        )

    if len(stripped_text) > max_length:
        raise ValidationError(
            f"Input text exceeds maximum length limit ({len(stripped_text)} / {max_length} characters)."
        )

    return stripped_text
