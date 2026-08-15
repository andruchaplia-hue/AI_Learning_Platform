import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import FileResponse

from backend.use_cases.use_case_3_image_captioning.models import ImageCaptionResponse
from backend.use_cases.use_case_3_image_captioning.service import ImageCaptionService

router = APIRouter(prefix="/api/v1/image-caption", tags=["Image Captioning"])
logger = logging.getLogger("backend.api.routes.image_caption")


def get_image_caption_service(request: Request) -> ImageCaptionService:
    """Dependency injector: reads ImageCaptionService singleton from app.state."""
    return request.app.state.image_caption_service


@router.post(
    "",
    response_model=ImageCaptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate natural language caption and description for an uploaded image",
)
async def generate_image_caption(
    file: UploadFile = File(...),
    service: ImageCaptionService = Depends(get_image_caption_service),
) -> ImageCaptionResponse:
    """Proxy request to ImageCaptionService for validation, storage, and vision LLM caption generation."""
    logger.info(f"Received image captioning upload request for file: {file.filename}")
    content_bytes = await file.read()
    return await service.generate_caption(
        content_bytes=content_bytes,
        filename=file.filename or "uploaded_image.png",
    )


@router.get(
    "/image/{image_path:path}",
    response_class=FileResponse,
    summary="Retrieve stored image file by relative path or ID",
)
async def get_stored_image(
    image_path: str,
    service: ImageCaptionService = Depends(get_image_caption_service),
) -> FileResponse:
    """Serve stored image file from local upload storage."""
    file_path: Path = service.storage_manager.get_file_path(image_path)
    return FileResponse(path=file_path)
