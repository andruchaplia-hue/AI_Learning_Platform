from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class FrameworkType(str, Enum):
    """Supported framework targets for LLM provider instantiation."""

    LANGCHAIN = "langchain"
    SEMANTIC_KERNEL = "semantic_kernel"


class BaseProvider(ABC):
    """Abstract interface for all LLM providers in Gateway layer."""

    @abstractmethod
    def get_llm(self, framework: FrameworkType = FrameworkType.LANGCHAIN) -> Any:
        """Return initialized LLM client or kernel for specified framework."""

