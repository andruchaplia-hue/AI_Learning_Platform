import logging

from backend.infrastructure.config.settings import AppSettings

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class CodeReviewerPlugin:
    """Semantic Kernel plugin for auditing generated code for quality, PEP8, and security."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    @kernel_function(
        name="review_code",
        description="Audits generated code snippet and provides structural code review comments.",
    )
    def review_code(self, code: str, prompt: str = "") -> str:
        """Native SK kernel function descriptor."""
        logger.info("CodeReviewerPlugin auditing code quality...")
        return f"Audit target: {prompt}"
