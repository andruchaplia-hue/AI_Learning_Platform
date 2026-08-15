import json
import logging
from pathlib import Path
from typing import Any

from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.memory.storage.base_repository import BaseFAQRepository
from backend.domain.models.faq import FAQItem

logger = logging.getLogger(__name__)


class FAQRepository(BaseFAQRepository):
    """Centralized repository for persistent FAQ dataset I/O and ID calculation."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.file_path = self._resolve_file_path()

    def _resolve_file_path(self) -> Path:
        """Resolve absolute path to data/faq.json anchored to project root."""
        # __file__ is in backend/infrastructure/memory/storage/
        project_root = Path(__file__).resolve().parents[4]
        configured_path = Path(self.settings.faq_json_path)

        if configured_path.is_absolute():
            path = configured_path
        else:
            path = project_root / configured_path

        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f)
        return path

    def load_all(self) -> list[FAQItem]:
        """Load all FAQ items from disk storage."""
        path = self._resolve_file_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
                return [FAQItem(**item) for item in data]
        except Exception as exc:
            logger.error(f"FAQRepository: Failed to load FAQ dataset from {path}: {exc}")
            return []

    def save_items(self, items: list[FAQItem]) -> list[FAQItem]:
        """Add or update FAQ items in persistent storage.

        Automatically assigns consecutive sequential IDs (max_id + 1) for new items (id <= 0).
        Returns the list of saved FAQItem objects complete with their assigned IDs.
        """
        existing_items = self.load_all()
        existing_questions = {elem.question.lower().strip("?,.!\n\r "): idx for idx, elem in enumerate(existing_items)}
        existing_ids = {elem.id: idx for idx, elem in enumerate(existing_items)}
        max_id = max([elem.id for elem in existing_items], default=0)

        saved_items: list[FAQItem] = []

        for item in items:
            q_key = item.question.lower().strip("?,.!\n\r ")
            
            if q_key in existing_questions:
                # Update existing question in-place
                idx = existing_questions[q_key]
                existing_items[idx].answer = item.answer
                existing_items[idx].category = item.category
                saved_items.append(existing_items[idx])
            elif item.id > 0 and item.id in existing_ids:
                # Update item by ID in-place
                idx = existing_ids[item.id]
                existing_items[idx].question = item.question
                existing_items[idx].answer = item.answer
                existing_items[idx].category = item.category
                saved_items.append(existing_items[idx])
            else:
                # Completely new item -> calculate new sequential ID
                max_id += 1
                new_item = FAQItem(
                    id=max_id,
                    category=item.category,
                    question=item.question,
                    answer=item.answer,
                )
                existing_items.append(new_item)
                new_idx = len(existing_items) - 1
                existing_questions[q_key] = new_idx
                existing_ids[max_id] = new_idx
                saved_items.append(new_item)

        # Write updated dataset to disk
        path = self._resolve_file_path()
        dump_data = [item.model_dump() for item in existing_items]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2, ensure_ascii=False)

        logger.info(f"FAQRepository: Successfully saved {len(saved_items)} items to {path}")
        return saved_items
