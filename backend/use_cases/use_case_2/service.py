import json
import logging
import re
import time
from typing import Any

from backend.domain.exceptions import ConfigurationError, ValidationError, ProviderError
from backend.domain.models.faq import FAQItem
from backend.domain.validators.text_validator import validate_input_text
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base_provider import FrameworkType
from backend.infrastructure.memory.sqlite.sqlite_memory import SQLiteMemory
from backend.infrastructure.memory.vectorstorage.chroma_store import ChromaStore
from backend.infrastructure.memory.vectorstorage.embedding_service import EmbeddingService
from backend.infrastructure.memory.storage.base_repository import BaseFAQRepository
from backend.infrastructure.memory.storage.faq_repository import FAQRepository
from backend.use_cases.use_case_2.agent import FAQAgent
from backend.use_cases.use_case_2.retriever import FAQRetriever
from backend.use_cases.use_case_2.models import (
    ExecutionDetails,
    FAQQueryRequest,
    FAQQueryResponse,
    RetrievedFAQ,
)
from backend.use_cases.use_case_2.plugins.faq_plugin import FAQPlugin
from backend.use_cases.use_case_2.prompt_loader import load_prompt


logger = logging.getLogger(__name__)


class FAQService:
    """Use Case Service orchestrating FAQ RAG pipeline with Semantic Kernel Agent and FAQRepository."""

    def __init__(self, settings: AppSettings, faq_repo: BaseFAQRepository | None = None):
        self.settings = settings
        self.memory = SQLiteMemory(db_path=settings.faq_memory_db_path)
        self.faq_repo = faq_repo or FAQRepository(settings)
        self.embedding_service = EmbeddingService(settings)
        self.vector_store = ChromaStore(settings, self.embedding_service)
        self.retriever = FAQRetriever(self.vector_store, self.embedding_service)
        self.faq_plugin = FAQPlugin(
            retriever=self.retriever,
            top_k=settings.faq_top_k,
            threshold=settings.faq_similarity_threshold,
        )
        self.agent = FAQAgent(settings, self.faq_plugin)

        # Auto-initialize vector store if empty
        self.ensure_index_loaded()

    def ensure_index_loaded(self, force_reload: bool = False) -> int:
        """Load FAQ entries from FAQRepository and index into vector store if empty."""
        if not self.vector_store.is_empty() and not force_reload:
            return len(self.vector_store.faq_items)

        items = self.faq_repo.load_all()
        self.vector_store.index_faqs(items)
        logger.info(f"FAQService: Indexed {len(items)} FAQ items from FAQRepository")
        return len(items)

    def add_faq_item(self, item: FAQItem) -> list[FAQItem]:
        """Add a single new FAQ item to repository and re-index vector store."""
        return self.bulk_add_faq_items([item])

    def bulk_add_faq_items(self, items: list[FAQItem]) -> list[FAQItem]:
        """Add multiple FAQ items to repository and re-index vector store, returning saved items with assigned IDs."""
        saved_items = self.faq_repo.save_items(items)
        self.ensure_index_loaded(force_reload=True)
        return saved_items

    async def parse_and_add_raw_text(self, raw_text: str) -> list[FAQItem]:
        """Parse unstructured text into structured Q&A FAQItems using Semantic Kernel.

        Saves items to repository with sequential IDs and re-indexes vector store.
        """
        text = raw_text.strip()
        if not text:
            raise ValidationError("Input text is empty. Enter text with questions and answers.")

        try:
            parse_template = load_prompt("parse_prompt.txt")
            formatted_prompt = parse_template.replace("{text}", text)

            provider = LLMGateway.get_provider(self.settings)
            kernel = provider.get_llm(framework=FrameworkType.SEMANTIC_KERNEL)

            raw_json = await self._call_sk_parse_llm(kernel, formatted_prompt)
            extracted_items = self._parse_faq_json(raw_json)
        except (ValidationError, ProviderError, ConfigurationError):
            raise
        except Exception as exc:
            logger.error(f"Semantic Kernel text parsing failed: {exc}", exc_info=True)
            raise ValidationError(
                "Could not extract question and answer structure from the provided text."
            ) from exc

        if not extracted_items:
            raise ValidationError(
                "Failed to extract any question-answer pairs from text."
            )

        saved_items = self.bulk_add_faq_items(extracted_items)
        return saved_items

    async def _call_sk_parse_llm(self, kernel: Any, prompt: str) -> str:
        """Invoke Semantic Kernel (or fallback LLM) with the parse prompt and return raw JSON string."""
        if hasattr(kernel, "add_function"):
            sk_func = kernel.add_function(
                function_name="parse_faq_text",
                plugin_name="FAQPlugin",
                prompt=prompt,
            )
            result = await kernel.invoke(sk_func)
            return str(result)

        # Fallback for non-SK kernels (e.g., LangChain BaseChatModel in mock mode)
        response = (
            await kernel.ainvoke(prompt)
            if hasattr(kernel, "ainvoke")
            else kernel.invoke(prompt)
        )
        return response.content if hasattr(response, "content") else str(response)

    def _parse_faq_json(self, raw_json: str) -> list[FAQItem]:
        """Extract and parse a JSON array of Q&A pairs from raw LLM output string."""
        json_match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', raw_json)
        if json_match:
            clean_json = json_match.group(1).strip()
        else:
            clean_json = re.sub(r"```(?:json)?|```", "", raw_json).strip()

        parsed_data = json.loads(clean_json)

        parsed_list: list[dict[str, Any]] = []
        if isinstance(parsed_data, list):
            parsed_list = parsed_data
        elif isinstance(parsed_data, dict):
            for key in ("faqs", "questions", "items", "data", "results"):
                if key in parsed_data and isinstance(parsed_data[key], list):
                    parsed_list = parsed_data[key]
                    break

        items: list[FAQItem] = []
        for elem in parsed_list:
            q = elem.get("question", "").strip()
            a = elem.get("answer", "").strip()
            if q and a:
                items.append(
                    FAQItem(
                        id=0,  # FAQRepository auto-assigns max_id + 1
                        category=elem.get("category", "General"),
                        question=q,
                        answer=a,
                    )
                )
        return items

    async def process_query(self, request: FAQQueryRequest) -> FAQQueryResponse:
        """Process incoming user query end-to-end."""
        start_time = time.time()
        query = validate_input_text(
            request.query,
            min_length=self.settings.min_length,
            max_length=self.settings.max_length,
        )

        session_id = request.session_id or "default_session"

        # Check if vector store is empty
        if self.vector_store.is_empty():
            return FAQQueryResponse(
                status="success",
                answer="No FAQ entries are currently available in the database.",
                found=False,
                session_id=session_id,
                execution_details=ExecutionDetails(
                    decomposed_queries=[],
                    retrieved_faqs=[],
                    max_similarity_score=0.0,
                    coverage_score=0.0,
                    is_fallback=True,
                    execution_time_seconds=round(time.time() - start_time, 3),
                ),
            )

        # Load session conversation history
        history = self.memory.get_history(session_id=session_id, limit=6)

        # Invoke SK Agent to orchestrate query decomposition, RAG, and coverage analysis
        try:
            answer_text, retrieved_faqs, is_found, metrics = await self.agent.invoke(
                query=query,
                chat_history=history,
                user_friendly=request.user_friendly,
                sk_filtering=request.sk_filtering,
            )
        except Exception as exc:
            logger.error(f"FAQAgent execution error: {exc}", exc_info=True)
            raise ProviderError(f"FAQ Assistant encountered an internal execution error: {exc}") from exc

        # Save exchange to SQLite Memory
        self.memory.save_message(session_id=session_id, role="user", content=query)
        self.memory.save_message(session_id=session_id, role="assistant", content=answer_text)

        elapsed = round(time.time() - start_time, 3)

        execution_details = ExecutionDetails(
            decomposed_queries=metrics.get("decomposed_queries", [query]),
            retrieved_faqs=retrieved_faqs,
            max_similarity_score=metrics.get("max_similarity_score", 0.0),
            coverage_score=metrics.get("coverage_score", 0.0),
            missing_questions=metrics.get("missing_questions", []),
            is_fallback=metrics.get("is_fallback", not is_found),
            sk_filtering=metrics.get("sk_filtering", request.sk_filtering),
            selected_faq_ids=metrics.get("selected_faq_ids", []),
            decomposer_fallback=metrics.get("decomposer_fallback", False),
            coverage_fallback=metrics.get("coverage_fallback", False),
            pipeline_error=metrics.get("pipeline_error", None),
            execution_time_seconds=elapsed,
        )

        return FAQQueryResponse(
            status="success",
            answer=answer_text,
            found=is_found,
            session_id=session_id,
            execution_details=execution_details,
        )

    def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        """Get history messages for session."""
        return self.memory.get_history(session_id=session_id, limit=20)

    def clear_session_history(self, session_id: str) -> None:
        """Clear memory for session."""
        self.memory.clear_session(session_id=session_id)
