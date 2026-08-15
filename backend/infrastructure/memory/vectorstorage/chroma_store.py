import json
import logging
import math
from pathlib import Path
from typing import Any

from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.memory.base import BaseVectorStore
from backend.infrastructure.memory.vectorstorage.embedding_service import EmbeddingService
from backend.use_cases.use_case_2.models import FAQItem, RetrievedFAQ

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity score between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class ChromaStore(BaseVectorStore):
    """ChromaDB & In-Memory Vector Store for indexing FAQ knowledge base and vector similarity search."""

    def __init__(self, settings: AppSettings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedding_service = embedding_service
        self.db_path = Path(settings.faq_vector_db_path)
        self.faq_items: list[FAQItem] = []
        self.embeddings_cache: list[list[float]] = []
        # Attempt to load previously persisted index from disk to avoid recalculating embeddings
        self.try_load_persisted_index()

    def is_empty(self) -> bool:
        """Check if vector store contains indexed FAQs."""
        return len(self.faq_items) == 0

    def try_load_persisted_index(self) -> bool:
        """Load persisted vectors from chroma_embeddings.json if available."""
        index_file = self.db_path / "chroma_embeddings.json"
        if not index_file.exists():
            return False
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or not data:
                return False

            loaded_faqs: list[FAQItem] = []
            loaded_embeddings: list[list[float]] = []
            for item_dict in data:
                loaded_faqs.append(
                    FAQItem(
                        id=item_dict.get("id"),
                        category=item_dict.get("category", "General"),
                        question=item_dict.get("question", ""),
                        answer=item_dict.get("answer", ""),
                    )
                )
                loaded_embeddings.append(item_dict.get("embedding", []))

            self.faq_items = loaded_faqs
            self.embeddings_cache = loaded_embeddings
            logger.info(f"Loaded {len(loaded_faqs)} cached FAQ vectors from {index_file} without re-embedding.")
            return True
        except Exception as exc:
            logger.warning(f"Failed to load cached vector store index from {index_file}: {exc}")
            return False

    def index_faqs(self, faqs: list[FAQItem]) -> None:
        """Index FAQ entries and store document embeddings."""
        logger.info(f"Indexing {len(faqs)} FAQ items into Vector Store...")
        self.faq_items = faqs
        self.embeddings_cache = []

        for item in faqs:
            doc_text = f"Category: {item.category}\nQuestion: {item.question}\nAnswer: {item.answer}"
            vec = self.embedding_service.embed_document(doc_text)
            self.embeddings_cache.append(vec)

        # Physically persist vector index to disk under self.db_path
        try:
            self.db_path.mkdir(parents=True, exist_ok=True)
            dump_data = [
                {
                    "id": item.id,
                    "category": item.category,
                    "question": item.question,
                    "answer": item.answer,
                    "embedding": vec,
                }
                for item, vec in zip(self.faq_items, self.embeddings_cache)
            ]
            index_file = self.db_path / "chroma_embeddings.json"
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Persisted vector store index physically to {index_file}")
        except Exception as exc:
            logger.warning(f"Failed to persist vector store index to disk: {exc}")

        logger.info(f"Successfully indexed {len(self.faq_items)} FAQs.")


    def search(self, query: str, top_k: int = 3, min_score: float = 0.0) -> list[RetrievedFAQ]:
        """Search top-K closest FAQs using vector cosine similarity."""
        if not self.faq_items:
            logger.warning("Vector Store search called on empty index")
            return []

        query_vec = self.embedding_service.embed_query(query)
        scored_results: list[RetrievedFAQ] = []

        for item, doc_vec in zip(self.faq_items, self.embeddings_cache):
            score = cosine_similarity(query_vec, doc_vec)
            norm_score = max(0.0, min(1.0, (score + 1.0) / 2.0 if score < 0 else score))

            if norm_score >= min_score:
                scored_results.append(
                    RetrievedFAQ(
                        id=item.id,
                        category=item.category,
                        question=item.question,
                        answer=item.answer,
                        score=round(norm_score, 4),
                    )
                )

        scored_results.sort(key=lambda x: x.score, reverse=True)
        return scored_results[:top_k]
