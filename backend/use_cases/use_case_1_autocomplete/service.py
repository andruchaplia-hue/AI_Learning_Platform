import logging
from pathlib import Path
import time

from backend.domain.exceptions import ProviderError, ConfigurationError
from backend.domain.validators.text_validator import validate_input_text
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base_provider import FrameworkType
from backend.use_cases.use_case_1_autocomplete.chain import create_autocomplete_chain
from backend.use_cases.use_case_1_autocomplete.models import (
    AutocompleteResponse,
    CompletionMode,
)
from backend.use_cases.use_case_1_autocomplete.utils import (
    split_options,
    clean_option_prefix,
    parse_provider_exception,
)

logger = logging.getLogger("backend.service.autocomplete")


def load_instruction(mode: str) -> str:
    """Load text prompt template from file based on mode."""
    filename = f"{mode}_instruction.txt"
    file_path = Path(__file__).resolve().parent / "prompts" / filename
    if not file_path.exists():
        raise ConfigurationError(f"Instruction template file not found at {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


class AutocompleteService:
    """Orchestrates input validation, LLM chain invocation, timing, and error handling for UC1."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.provider = LLMGateway.get_provider(settings)
        self.chain = create_autocomplete_chain(
            self.provider.get_llm(framework=FrameworkType.LANGCHAIN)
        )

    async def generate_autocomplete(
        self, raw_text: str, mode: CompletionMode | str = CompletionMode.SENTENCE
    ) -> AutocompleteResponse:
        """Validate input text, run LCEL chain asynchronously, and measure execution time.

        Args:
            raw_text: User input text to complete.
            mode: Completion mode: 'sentence' or 'paragraph'.

        Returns:
            AutocompleteResponse containing completion text and execution_time_sec.

        Raises:
            ValidationError: If raw_text fails domain rules.
            ProviderError: If the underlying LLM provider call fails.
        """
        valid_text = validate_input_text(
            raw_text,
            min_length=self.settings.min_length,
            max_length=self.settings.max_length,
        )

        mode_str = mode.value if hasattr(mode, "value") else str(mode)
        instruction = load_instruction(mode_str)

        logger.info(
            f"Invoking LLM provider '{self.settings.provider}' for UC1 completion in '{mode_str}' mode."
        )
        start_time = time.perf_counter()

        try:
            completion_result = await self.chain.ainvoke(
                {"text": valid_text, "instruction": instruction}
            )
        except ProviderError:
            raise
        except Exception as exc:
            logger.exception("Error during LLM invocation in UC1")
            raise ProviderError(parse_provider_exception(exc)) from exc

        elapsed_time = round(time.perf_counter() - start_time, 3)
        logger.info(f"UC1 chain completed successfully in {elapsed_time}s.")

        clean_completion = str(completion_result).strip()
        options = split_options(clean_completion)
        main_completion = options[0] if options else clean_completion

        return AutocompleteResponse(
            completion=main_completion,
            completions=options,
            execution_time_sec=elapsed_time,
        )
