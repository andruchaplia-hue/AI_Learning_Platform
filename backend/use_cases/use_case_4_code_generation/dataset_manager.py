import json
import logging
import re
from pathlib import Path
from typing import Any

from backend.domain.exceptions import ConfigurationError, ValidationError
from backend.infrastructure.config.settings import AppSettings
from backend.use_cases.use_case_4_code_generation.models import DatasetEntry

logger = logging.getLogger(__name__)


class DatasetManager:
    """Manages reading, appending, validating, and monitoring fine-tuning JSONL dataset pairs."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        root_dir = Path(__file__).resolve().parents[3]
        rel_path = Path(settings.code_gen_dataset_path)
        self.dataset_path = rel_path if rel_path.is_absolute() else (root_dir / rel_path)
        self.metadata_path = self.dataset_path.parent / "tuned_model_metadata.json"

    def _ensure_file_exists(self) -> None:
        """Create dataset directory and empty file if missing."""
        try:
            self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.dataset_path.exists():
                self.dataset_path.touch()
        except Exception as exc:
            raise ConfigurationError(f"Failed to initialize dataset file path {self.dataset_path}: {exc}") from exc

    def get_metadata(self) -> dict[str, Any]:
        """Read metadata JSON for fine-tuned model ID and status."""
        if not self.metadata_path.exists():
            return {
                "active_tuned_model_id": "",
                "last_updated": None,
                "dataset_size": 0,
                "status": "UNINITIALIZED",
            }
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "active_tuned_model_id": "",
                "last_updated": None,
                "dataset_size": 0,
                "status": "UNINITIALIZED",
            }

    def save_metadata(self, active_tuned_model_id: str, status: str = "READY", message: str = "") -> dict[str, Any]:
        """Persist fine-tuned model ID and status metadata."""
        import datetime

        entries = self.get_dataset_entries()
        data = {
            "active_tuned_model_id": active_tuned_model_id,
            "last_updated": datetime.datetime.utcnow().isoformat(),
            "dataset_size": len(entries),
            "status": status,
            "message": message,
        }
        try:
            self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"Failed to save metadata to {self.metadata_path}: {exc}")
        return data

    def get_dataset_entries(self) -> list[DatasetEntry]:

        """Read and parse JSONL training pairs into DatasetEntry list."""
        self._ensure_file_exists()
        entries: list[DatasetEntry] = []
        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f, 1):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        messages = data.get("messages", [])
                        user_prompt = ""
                        expected_code = ""
                        for msg in messages:
                            if msg.get("role") == "user":
                                user_prompt = msg.get("content", "")
                            elif msg.get("role") == "assistant":
                                expected_code = msg.get("content", "")
                        if user_prompt and expected_code:
                            entries.append(
                                DatasetEntry(
                                    id=idx,
                                    user_prompt=user_prompt,
                                    expected_code=expected_code,
                                )
                            )
                    except json.JSONDecodeError as err:
                        logger.warning(f"Skipping malformed JSON line {idx} in {self.dataset_path}: {err}")
        except Exception as exc:
            raise ConfigurationError(f"Failed to read fine-tuning dataset file: {exc}") from exc
        return entries

    def add_dataset_entry(self, user_prompt: str, expected_code: str) -> DatasetEntry:
        """Validate and append a new JSONL training pair entry."""
        if not user_prompt.strip() or len(user_prompt.strip()) < 5:
            raise ValidationError("User prompt must be at least 5 characters long.")
        if not expected_code.strip() or len(expected_code.strip()) < 5:
            raise ValidationError("Expected code must be at least 5 characters long.")

        self._ensure_file_exists()
        existing_entries = self.get_dataset_entries()
        new_id = len(existing_entries) + 1

        new_record = {
            "messages": [
                {"role": "user", "content": user_prompt.strip()},
                {"role": "assistant", "content": expected_code.strip()},
            ]
        }

        try:
            with open(self.dataset_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(new_record, ensure_ascii=False) + "\n")
        except Exception as exc:
            raise ConfigurationError(f"Failed to write entry to dataset file: {exc}") from exc

        return DatasetEntry(id=new_id, user_prompt=user_prompt.strip(), expected_code=expected_code.strip())

    def find_similar_examples(self, prompt: str, top_k: int = 3) -> list[DatasetEntry]:
        """Retrieve top-k most semantically relevant training examples using keyword overlap scoring.

        This implements the RAG (Retrieval-Augmented Generation) retrieval step for the
        few-shot prompting pipeline. Entries are ranked by the count of shared tokens
        (lowercased, non-punctuation) between the query prompt and each training pair's
        user_prompt. Only entries with at least one overlapping keyword are returned.

        Args:
            prompt: The natural language generation request to match against.
            top_k: Maximum number of examples to return.

        Returns:
            List of up to top_k DatasetEntry objects, sorted by relevance descending.
        """
        entries = self.get_dataset_entries()
        if not entries:
            return []

        # Tokenise: lowercase alphanum words, ignore stop-words
        _STOP = {
            "a", "an", "the", "is", "in", "on", "at", "to", "of", "for",
            "and", "or", "with", "this", "that", "it", "be", "as", "by",
        }

        def _tokens(text: str) -> set[str]:
            return {
                w for w in re.findall(r"[a-z0-9]+", text.lower())
                if w not in _STOP and len(w) > 1
            }

        query_tokens = _tokens(prompt)
        scored: list[tuple[int, DatasetEntry]] = []

        for entry in entries:
            entry_tokens = _tokens(entry.user_prompt)
            # Weighted score: exact match tokens count double
            overlap = len(query_tokens & entry_tokens)
            if overlap > 0:
                scored.append((overlap, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        result = [entry for _, entry in scored[:top_k]]
        logger.debug(
            f"RAG retrieval for prompt '{prompt[:60]}': "
            f"found {len(result)} examples from {len(entries)} total."
        )
        return result

    def get_job_status(self) -> dict[str, Any]:
        """Return dataset size and fine-tuning target model status from metadata."""
        entries = self.get_dataset_entries()
        meta = self.get_metadata()
        active_id = meta.get("active_tuned_model_id", "")
        status_msg = meta.get("message") or (
            f"Active Tuned Model: '{active_id}'" if active_id else "No fine-tuned model trained yet. Trigger training to start."
        )
        return {
            "status": meta.get("status", "ready"),
            "message": status_msg,
            "dataset_size": len(entries),
            "tuned_model_id": active_id,
        }

