import logging

from backend.infrastructure.config.settings import AppSettings

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class CodeGeneratorPlugin:
    """Semantic Kernel plugin for generating code snippets or refactoring source code."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    @kernel_function(
        name="generate_code",
        description="Generates production-grade code snippet or performs refactoring on existing target content.",
    )
    def generate_code(self, prompt: str, requirements_json: str = "", target_content: str = "") -> str:
        """Native SK kernel function descriptor."""
        logger.info(f"CodeGeneratorPlugin invoked for prompt: {prompt[:50]}...")
        return f"Code generation target: {prompt}"
