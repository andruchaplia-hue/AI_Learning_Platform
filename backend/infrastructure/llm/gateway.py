import logging
from typing import Any

from backend.domain.exceptions import ConfigurationError
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.llm.providers.base_provider import BaseProvider, FrameworkType
from backend.infrastructure.llm.providers.google_provider import GoogleProvider
from backend.infrastructure.llm.providers.mock_provider import MockProvider

logger = logging.getLogger(__name__)


class LLMGateway:
    """Factory and gateway for dynamically loading LLM providers based on settings."""

    @staticmethod
    def get_provider(settings: AppSettings, model_name: str | None = None) -> BaseProvider:
        provider_name = settings.provider.lower().strip()
        logger.info(f"Initializing LLM Provider: {provider_name} (model: {model_name or settings.google_model})")

        if provider_name == "google":
            target_model = model_name or settings.google_model
            return GoogleProvider(
                api_key=settings.google_api_key,
                model_name=target_model,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                timeout=settings.timeout_seconds,
            )
        elif provider_name == "mock":
            # If mock, we can pass model_name down to MockProvider if it supports it
            return MockProvider(model_name=model_name or "mock-model")
        else:
            raise ConfigurationError(
                f"Unsupported LLM provider '{provider_name}'. Supported options are: 'google', 'mock'."
            )

    @staticmethod
    def get_llm(
        settings: AppSettings,
        framework: FrameworkType = FrameworkType.LANGCHAIN,
        model_name: str | None = None,
    ) -> Any:
        """Helper method to directly instantiate and return LLM client for specified framework."""
        provider = LLMGateway.get_provider(settings, model_name=model_name)
        return provider.get_llm(framework=framework)

