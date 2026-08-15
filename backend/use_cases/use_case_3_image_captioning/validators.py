from backend.infrastructure.storage.image_service import ImageService

_default_image_service = ImageService()


def validate_image_file(
    content_bytes: bytes,
    filename: str,
    max_file_size_mb: int = 10,
    allowed_formats: list[str] | None = None,
) -> str:
    """Validate raw image bytes, checking format, size limit, and PIL readability."""
    return _default_image_service.validate_image(
        content_bytes=content_bytes,
        filename=filename,
        max_file_size_mb=max_file_size_mb,
        allowed_formats=allowed_formats,
    )

