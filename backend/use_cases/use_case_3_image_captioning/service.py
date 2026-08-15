import logging
import time

from backend.domain.exceptions import ProviderError
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base_provider import FrameworkType
from backend.infrastructure.storage.local_storage import LocalStorageManager
from backend.use_cases.use_case_3_image_captioning.chain import create_image_caption_chain
from backend.use_cases.use_case_3_image_captioning.image_processor import process_image
from backend.use_cases.use_case_3_image_captioning.models import ImageCaptionResponse
from backend.use_cases.use_case_3_image_captioning.utils import parse_caption_output
from backend.use_cases.use_case_3_image_captioning.validators import validate_image_file

logger = logging.getLogger("backend.service.image_caption")


class ImageCaptionService:
    """Orchestrates image validation, local storage, LLM vision chain invocation, and metrics for UC3."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.provider = LLMGateway.get_provider(settings)
        self.chain = create_image_caption_chain(
            self.provider.get_llm(framework=FrameworkType.LANGCHAIN)
        )
        self.storage_manager = LocalStorageManager(
            upload_dir=settings.image_captioning_upload_dir
        )

    async def generate_caption(
        self, content_bytes: bytes, filename: str = "image.png"
    ) -> ImageCaptionResponse:
        """Validate, resize, store image and generate descriptive caption via LangChain vision chain.

        Args:
            content_bytes: Uploaded image bytes.
            filename: Original filename.

        Returns:
            ImageCaptionResponse DTO object.
        """
        validate_image_file(
            content_bytes,
            filename=filename,
            max_file_size_mb=self.settings.image_captioning_max_file_size_mb,
            allowed_formats=self.settings.image_captioning_allowed_formats,
        )

        proc_result = process_image(
            content_bytes,
            filename=filename,
            max_dimension=self.settings.image_captioning_max_dimension,
        )

        image_id = self.storage_manager.save_file(
            proc_result.processed_bytes, original_filename=filename
        )

        start_time = time.perf_counter()
        logger.info(
            f"Invoking LLM provider '{self.settings.provider}' for image captioning (image_id: {image_id})."
        )

        try:
            raw_response = await self.chain.ainvoke(
                {
                    "image_base64": proc_result.base64_str,
                    "mime_type": proc_result.mime_type,
                }
            )
        except Exception as exc:
            logger.exception(f"Error during LLM vision invocation for image {image_id}")
            raise ProviderError(f"Failed to generate image caption: {exc}") from exc

        elapsed_time = round(time.perf_counter() - start_time, 3)

        short_caption, full_description, action_description = parse_caption_output(str(raw_response))

        return ImageCaptionResponse(
            short_caption=short_caption,
            full_description=full_description,
            action_description=action_description,
            execution_time_sec=elapsed_time,
            resized=proc_result.resized,
            original_resolution=proc_result.original_resolution,
            processed_resolution=proc_result.processed_resolution,
            image_id=image_id,
        )

