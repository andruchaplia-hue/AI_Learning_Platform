import json
import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.infrastructure.auth.user_repository import UserRepository
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.memory.vectorstorage.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class PersonalizationDatasetService:
    """Manages personal writing samples, ChromaDB vector indexing and retrieval for few-shot personalization."""

    def __init__(
        self,
        settings: AppSettings,
        user_repo: UserRepository,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.settings = settings
        self.user_repo = user_repo
        self.embedding_service = embedding_service or EmbeddingService(settings)
        self.collection_prefix = settings.content_gen_vector_collection_prefix
        self._client = None
        try:
            self._client = chromadb.PersistentClient(
                path=settings.faq_vector_db_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        except Exception as exc:
            logger.warning(f"Failed to initialize ChromaDB PersistentClient: {exc}")

    def _get_collection_name(self, user_id: str) -> str:
        safe_id = user_id.replace("-", "_")
        return f"{self.collection_prefix}{safe_id}"

    def _get_or_create_collection(self, user_id: str):
        if not self._client:
            return None
        col_name = self._get_collection_name(user_id)
        return self._client.get_or_create_collection(
            name=col_name, metadata={"hnsw:space": "cosine"}
        )

    def index_vector_sample(
        self,
        sample_id: str,
        user_id: str,
        title: str,
        content_type: str,
        content: str,
        tags: list[str] | None = None,
    ) -> None:
        """Index a sample document vector in ChromaDB without creating a new SQLite record."""
        try:
            col = self._get_or_create_collection(user_id)
            if col:
                text_to_embed = f"{title}\n\n{content}"
                emb = self.embedding_service.embed_document(text_to_embed)
                col.upsert(
                    ids=[sample_id],
                    embeddings=[emb],
                    documents=[content],
                    metadatas=[
                        {
                            "title": title,
                            "content_type": content_type,
                            "tags": ",".join(tags or []),
                        }
                    ],
                )
        except Exception as exc:
            logger.warning(f"Failed to index sample in ChromaDB: {exc}", exc_info=True)

    def add_writing_sample(
        self,
        user_id: str,
        title: str,
        content_type: str,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Save manual sample to SQLite and index vector embedding in ChromaDB."""
        sample = self.user_repo.save_writing_sample(
            user_id=user_id,
            title=title,
            content_type=content_type,
            content=content,
            tags=tags or [],
        )
        self.index_vector_sample(
            sample_id=sample["id"],
            user_id=user_id,
            title=title,
            content_type=content_type,
            content=content,
            tags=tags,
        )
        return sample

    def delete_writing_sample(self, sample_id: str, user_id: str) -> bool:
        """Remove sample from SQLite and ChromaDB."""
        deleted = self.user_repo.delete_writing_sample(sample_id, user_id)
        if deleted:
            try:
                col = self._get_or_create_collection(user_id)
                if col:
                    col.delete(ids=[sample_id])
            except Exception as exc:
                logger.warning(f"Failed to delete sample from ChromaDB: {exc}")
        return deleted

    def list_writing_samples(self, user_id: str) -> list[dict[str, Any]]:
        """List all saved writing samples for user."""
        return self.user_repo.list_writing_samples(user_id)

    def find_similar_samples(
        self, user_id: str, query_text: str, top_k: int = 2
    ) -> list[dict[str, Any]]:
        """Search ChromaDB for the most relevant personal writing samples."""
        col = self._get_or_create_collection(user_id)
        if not col or col.count() == 0:
            # Fallback to recent SQLite samples if vector store is empty
            all_samples = self.user_repo.list_writing_samples(user_id)
            return all_samples[:top_k]

        try:
            query_emb = self.embedding_service.embed_query(query_text)
            results = col.query(
                query_embeddings=[query_emb],
                n_results=min(top_k, col.count()),
            )

            matched_samples = []
            if results and results.get("ids") and results["ids"][0]:
                for i, sample_id in enumerate(results["ids"][0]):
                    doc = results["documents"][0][i] if results.get("documents") else ""
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    matched_samples.append(
                        {
                            "id": sample_id,
                            "user_id": user_id,
                            "title": meta.get("title", ""),
                            "content_type": meta.get("content_type", ""),
                            "content": doc,
                            "tags": meta.get("tags", "").split(",") if meta.get("tags") else [],
                        }
                    )
            return matched_samples
        except Exception as exc:
            logger.warning(f"ChromaDB similarity search error: {exc}", exc_info=True)
            return self.user_repo.list_writing_samples(user_id)[:top_k]

    def export_dataset_jsonl(self, user_id: str) -> str:
        """Export user history items marked as few-shot samples as JSONL fine-tuning dataset."""
        samples = self.user_repo.list_writing_samples(user_id)

        lines = []
        for s in samples:
            item = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Write a {s['content_type']} about: {s['title']}",
                    },
                    {"role": "assistant", "content": s["content"]},
                ]
            }
            lines.append(json.dumps(item, ensure_ascii=False))

        return "\n".join(lines)
