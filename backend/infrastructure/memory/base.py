from abc import ABC, abstractmethod
from typing import Any

from backend.use_cases.use_case_2.models import FAQItem, RetrievedFAQ


class BaseMemoryStore(ABC):
    """Abstract interface for Conversation Memory Store implementations."""

    @abstractmethod
    def save_message(self, session_id: str, role: str, content: str) -> None:
        """Save a chat message to session memory."""
        pass

    @abstractmethod
    def get_history(self, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        """Retrieve recent conversation history for session."""
        pass

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """Clear all messages for a session."""
        pass


class BaseVectorStore(ABC):
    """Abstract interface for Vector Memory Store implementations."""

    @abstractmethod
    def is_empty(self) -> bool:
        """Check if vector index contains documents."""
        pass

    @abstractmethod
    def index_faqs(self, faqs: list[FAQItem]) -> None:
        """Index FAQ documents into vector store."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 3, min_score: float = 0.0) -> list[RetrievedFAQ]:
        """Search vector database for closest documents matching query."""
        pass
