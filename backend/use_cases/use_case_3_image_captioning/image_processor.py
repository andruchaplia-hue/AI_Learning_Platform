from backend.infrastructure.storage.image_service import ImageService, ProcessedImage

ProcessedImageResult = ProcessedImage
_default_image_service = ImageService()


def process_image(
    content_bytes: bytes,
    filename: str,
    max_dimension: int = 2048,
) -> ProcessedImageResult:
    """Normalize color space, downscale if dimensions exceed max_dimension, and generate base64 payload."""
    return _default_image_service.process_image(
        content_bytes=content_bytes,
        filename=filename,
        max_dimension=max_dimension,
    )

