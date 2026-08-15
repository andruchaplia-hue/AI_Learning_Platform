# Re-export alias for backward compatibility.
# Canonical implementation lives in vectorstorage/embedding_service.py.
from backend.infrastructure.memory.vectorstorage.embedding_service import EmbeddingService

__all__ = ["EmbeddingService"]
