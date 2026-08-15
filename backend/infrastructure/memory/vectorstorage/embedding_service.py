import logging
import math

from backend.infrastructure.config.settings import AppSettings
from backend.domain.exceptions import ConfigurationError, ProviderError

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding generation service for FAQ vector indexing and retrieval.

    Supports two modes controlled by ``settings.provider``:
    - ``google``: Uses Google GenAI embedding API (real embeddings).
    - ``mock``:   Uses a deterministic pseudo-embedding for local development
                  and offline operation.
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._is_mock = settings.provider.lower().strip() == "mock"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def embed_document(self, text: str) -> list[float]:
        """Generate document embedding for indexing (task_type=RETRIEVAL_DOCUMENT)."""
        if self._is_mock:
            return self._generate_mock_embedding(text)
        formatted = f"Represent this FAQ question for retrieval.\n\nQuestion:\n{text}"
        return self._embed_google(formatted, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        """Generate query embedding for searching (task_type=RETRIEVAL_QUERY)."""
        if self._is_mock:
            return self._generate_mock_embedding(text)
        formatted = f"Represent this user question for FAQ retrieval.\n\nQuestion:\n{text}"
        return self._embed_google(formatted, task_type="RETRIEVAL_QUERY")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _embed_google(self, text: str, task_type: str) -> list[float]:
        """Call Google GenAI embedding API and return the embedding vector."""
        if not self.settings.google_api_key:
            raise ConfigurationError(
                "Google API key is missing. Cannot generate live embeddings. "
                "Set GOOGLE_API_KEY in .env or switch provider to 'mock' in config.yaml."
            )
        try:
            try:
                from google import genai

                client = genai.Client(api_key=self.settings.google_api_key)
                model_name = self.settings.faq_embedding_model
                res = client.models.embed_content(model=model_name, contents=text)
                return res.embeddings[0].values
            except ImportError:
                import google.generativeai as genai  # type: ignore[no-redef]

                genai.configure(api_key=self.settings.google_api_key)
                model_name = self.settings.faq_embedding_model
                result = genai.embed_content(
                    model=f"models/{model_name}", content=text, task_type=task_type
                )
                return result["embedding"]
        except (ConfigurationError, ProviderError):
            raise
        except Exception as exc:
            logger.error(f"Google Embedding API failed: {exc}", exc_info=True)
            raise ProviderError(f"Google Embedding API call failed: {exc}") from exc

    @staticmethod
    def _generate_mock_embedding(text: str, dim: int = 1536) -> list[float]:
        """Generate a deterministic pseudo-embedding vector for mock/offline mode.

        The vector is reproducible for the same input text, which means
        cosine similarity works predictably in tests and local development.
        """
        seed = sum(ord(c) for c in text)
        vec = [math.sin(seed + i * 0.1) for i in range(dim)]
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm > 0 else vec
