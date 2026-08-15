import logging

from backend.infrastructure.config.settings import AppSettings

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class ImprovementAdvisorPlugin:
    """Semantic Kernel plugin for suggesting actionable improvement recommendations."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    @kernel_function(
        name="suggest_improvements",
        description="Generates actionable bulleted suggestions to extend or optimize the generated code.",
    )
    def suggest_improvements(self, code: str, review_comments: str = "") -> str:
        """Native SK kernel function descriptor."""
        logger.info("ImprovementAdvisorPlugin generating recommendations...")
        return "Improvement suggestions descriptor"
