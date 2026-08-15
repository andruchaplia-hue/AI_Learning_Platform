from abc import ABC, abstractmethod
from backend.use_cases.use_case_2.models import FAQItem


class BaseFAQRepository(ABC):
    """Abstract interface defining standard CRUD operations for FAQ data persistence."""

    @abstractmethod
    def load_all(self) -> list[FAQItem]:
        """Load all FAQ items from persistent storage."""
        pass

    @abstractmethod
    def save_items(self, items: list[FAQItem]) -> list[FAQItem]:
        """Save or update a list of FAQ items in persistent storage.

        Must assign unique IDs to new items (id <= 0) and return saved items.
        """
        pass
