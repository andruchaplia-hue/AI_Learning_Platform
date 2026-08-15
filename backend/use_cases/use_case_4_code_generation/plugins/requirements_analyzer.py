import json
import logging

from backend.infrastructure.config.settings import AppSettings

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class RequirementsAnalyzerPlugin:
    """Semantic Kernel plugin for extracting technical requirements from natural language."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    @kernel_function(
        name="analyze_requirements",
        description="Analyzes natural language prompt and extracts technical constraints, language, framework, and key functions.",
    )
    def analyze_requirements(self, prompt: str, target_content: str = "") -> str:
        """Extract structured requirements descriptor."""
        logger.info(f"RequirementsAnalyzerPlugin analyzing prompt: {prompt[:50]}...")
        return json.dumps({
            "language": "python",
            "framework": "standard",
            "key_functions": ["main"],
            "constraints": ["PEP8"],
            "prompt": prompt,
        }, ensure_ascii=False)
