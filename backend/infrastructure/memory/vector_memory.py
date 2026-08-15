# Re-export alias for backward compatibility.
# Canonical implementation lives in vectorstorage/chroma_store.py.
from backend.infrastructure.memory.vectorstorage.chroma_store import ChromaStore

__all__ = ["ChromaStore"]
