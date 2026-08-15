import difflib
import logging
import time
from typing import Any

from backend.domain.exceptions import ValidationError
from backend.infrastructure.config.settings import AppSettings
from backend.use_cases.use_case_4_code_generation.agent import CodeGenerationAgent
from backend.use_cases.use_case_4_code_generation.dataset_manager import DatasetManager
from backend.use_cases.use_case_4_code_generation.models import (
    AddDatasetEntryRequest,
    CodeGenerationRequest,
    CodeGenerationResponse,
    DatasetListResponse,
    FineTuneJobResponse,
)

logger = logging.getLogger(__name__)


class CodeGenerationService:
    """Service layer executing UC4 Code Generation agent pipeline, dataset management, and diff computation."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.dataset_manager = DatasetManager(settings)

    def compute_diff(self, original_text: str, modified_text: str, filename: str = "target_file.py") -> str:
        """Compute unified diff string between original and modified code content."""
        old_lines = original_text.splitlines(keepends=True)
        new_lines = modified_text.splitlines(keepends=True)
        diff_lines = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
        return "".join(diff_lines)

    async def generate_code(self, request: CodeGenerationRequest) -> CodeGenerationResponse:
        """Execute code generation or refactor request through SK agent pipeline.

        When model_mode='tuned', retrieves relevant few-shot examples from the JSONL training
        dataset via keyword-overlap RAG and injects them into the Code Generator prompt.
        This implements the RAG Few-Shot Prompting approach as a production-grade alternative
        to managed fine-tuning (which is unavailable on the current API tier).
        """
        start_time = time.perf_counter()

        if not request.prompt or len(request.prompt.strip()) < 3:
            raise ValidationError("Prompt must be at least 3 characters long.")

        target_model = self.settings.google_model
        few_shot_examples = []
        is_rag_mode = False

        if request.model_mode == "tuned":
            # RAG Few-Shot mode: retrieve relevant training examples from dataset
            few_shot_examples = self.dataset_manager.find_similar_examples(
                request.prompt, top_k=3
            )
            is_rag_mode = True
            logger.info(
                f"CodeGenerationService [TUNED/RAG] mode: retrieved {len(few_shot_examples)} "
                f"few-shot examples for prompt: '{request.prompt[:60]}'"
            )

        logger.info(f"CodeGenerationService executing prompt (mode={request.model_mode}, model={target_model})")

        agent = CodeGenerationAgent(self.settings, model_name=target_model)
        target_content = request.target_file_content or ""
        generated_code, reqs, review, suggestions = await agent.run_pipeline(
            prompt=request.prompt,
            target_content=target_content,
            few_shot_examples=few_shot_examples if is_rag_mode else None,
        )

        diff_str: str | None = None
        if request.target_file_content:
            filename = request.target_filename or "target_file.py"
            diff_str = self.compute_diff(request.target_file_content, generated_code, filename=filename)

        elapsed = time.perf_counter() - start_time

        return CodeGenerationResponse(
            status="success",
            generated_code=generated_code,
            diff=diff_str,
            requirements=reqs,
            review_comments=review,
            suggestions=suggestions,
            model_used=target_model,
            execution_time_sec=round(elapsed, 4),
            is_tuned_fallback=is_rag_mode,
        )


    def get_dataset(self) -> DatasetListResponse:
        """Fetch all entries in fine-tuning dataset."""
        entries = self.dataset_manager.get_dataset_entries()
        return DatasetListResponse(
            status="success",
            total_entries=len(entries),
            entries=entries,
        )

    def add_dataset_entry(self, request: AddDatasetEntryRequest) -> dict[str, Any]:
        """Add new training pair to dataset."""
        entry = self.dataset_manager.add_dataset_entry(request.user_prompt, request.expected_code)
        return {
            "status": "success",
            "message": "Dataset entry added successfully.",
            "entry": entry,
        }

    def trigger_fine_tune_job(self) -> FineTuneJobResponse:
        """Activate RAG few-shot mode by indexing the current training dataset.

        Since managed fine-tuning is unavailable on the current API tier, this method
        validates the dataset integrity and marks the RAG-based few-shot mode as READY.
        The dataset entries are used at inference time via keyword-overlap retrieval
        (find_similar_examples) and injected into the Code Generator prompt.
        """
        entries = self.dataset_manager.get_dataset_entries()
        dataset_size = len(entries)

        if dataset_size == 0:
            raise ValidationError(
                "Dataset is empty. Add at least 1 training example before activating few-shot mode."
            )

        # Persist READY status with RAG mode indicator
        self.dataset_manager.save_metadata(
            active_tuned_model_id="rag-few-shot",
            status="READY",
            message=(
                f"RAG Few-Shot mode activated with {dataset_size} training example(s). "
                "The dataset is retrieved at inference time and injected into the generator prompt. "
                "Add more examples to the dataset to improve generation quality."
            ),
        )

        logger.info(f"RAG Few-Shot mode activated: {dataset_size} examples indexed.")

        return FineTuneJobResponse(
            status="success",
            message=(
                f"✅ RAG Few-Shot mode activated with {dataset_size} training example(s). "
                "Switch to 'Fine-Tuned Model' in the Code Assistant tab to use it."
            ),
            dataset_size=dataset_size,
            tuned_model_id="rag-few-shot",
        )
