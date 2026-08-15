import logging
from typing import Any

from backend.infrastructure.memory.vectorstorage.chroma_store import ChromaStore
from backend.infrastructure.memory.vectorstorage.embedding_service import EmbeddingService
from backend.use_cases.use_case_2.models import RetrievedFAQ

logger = logging.getLogger(__name__)


class FAQRetriever:
    """Retrieves relevant FAQ records using embedding-based vector similarity search."""

    def __init__(self, chroma_store: ChromaStore, embedding_service: EmbeddingService):
        self.chroma_store = chroma_store
        self.embedding_service = embedding_service

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.75) -> list[RetrievedFAQ]:
        """Search closest FAQs using Query Instruction embeddings and similarity threshold."""
        logger.info(f"FAQRetriever: searching for '{query}' with top_k={top_k}, min_score={min_score}")
        
        # ChromaStore search calls embed_query which uses our Query Instruction template
        results = self.chroma_store.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
        )
        return results
