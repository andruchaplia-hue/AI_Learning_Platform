import base64
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.domain.exceptions import ValidationError
from backend.infrastructure.auth.user_repository import UserRepository
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.storage.image_service import ImageService
from backend.use_cases.use_case_5_content_gen.agent import ContentAgentPipeline
from backend.use_cases.use_case_5_content_gen.dataset_service import PersonalizationDatasetService
from backend.use_cases.use_case_5_content_gen.models import (
    ContentFeedbackRequest,
    ContentGenerationRequest,
    ContentGenerationResponse,
    ContentHistoryItem,
    ContentSubmitRequest,
)

logger = logging.getLogger(__name__)


class ContentGenerationService:
    """Core domain service for Use Case 5: Personalized Content Generation pipeline."""

    def __init__(
        self,
        settings: AppSettings,
        user_repo: UserRepository | None = None,
        dataset_service: PersonalizationDatasetService | None = None,
        agent_pipeline: ContentAgentPipeline | None = None,
        image_service: ImageService | None = None,
    ) -> None:
        self.settings = settings
        self.user_repo = user_repo or UserRepository(db_path=settings.faq_memory_db_path)
        self.dataset_service = dataset_service or PersonalizationDatasetService(
            settings, self.user_repo
        )
        self.agent_pipeline = agent_pipeline or ContentAgentPipeline(settings)
        self.image_service = image_service or ImageService(
            base_upload_dir=settings.image_captioning_upload_dir
        )

    # -------------------------------------------------------------------------
    # Content Generation & Agent Pipeline
    # -------------------------------------------------------------------------

    async def generate_content(
        self, user_id: str, req: ContentGenerationRequest
    ) -> ContentGenerationResponse:
        """Execute personalized content generation pipeline."""
        start_time = time.perf_counter()

        # Validate content type
        content_type = req.content_type.lower().strip()
        if content_type not in self.settings.content_gen_allowed_content_types:
            raise ValidationError(
                f"Unsupported content type '{req.content_type}'. "
                f"Allowed types: {self.settings.content_gen_allowed_content_types}"
            )

        if not req.prompt or len(req.prompt.strip()) < self.settings.min_length:
            raise ValidationError(f"Prompt must be at least {self.settings.min_length} characters")

        if len(req.prompt) > self.settings.content_gen_max_prompt_length:
            raise ValidationError(
                f"Prompt exceeds max allowed length ({self.settings.content_gen_max_prompt_length} chars)"
            )

        # 1. Fetch user profile
        profile = self.user_repo.get_user_profile(user_id)
        if not profile:
            raise ValidationError("User profile not found for generation")

        # 2. Personalization RAG: Fetch relevant writing samples
        few_shot_examples: list[dict[str, Any]] = []
        if req.use_personalization_dataset:
            few_shot_examples = self.dataset_service.find_similar_samples(
                user_id=user_id,
                query_text=req.prompt,
                top_k=self.settings.content_gen_top_k_examples,
            )

        # 3. Vision Understanding (Optional)
        visual_context = ""
        saved_image_path = ""
        if req.image_base64:
            try:
                raw_img_bytes = base64.b64decode(req.image_base64)
            except Exception as exc:
                raise ValidationError(f"Invalid base64 encoded image data: {exc}") from exc

            # Validate and optimize image dimensions for token and network economy
            self.image_service.validate_image(
                content_bytes=raw_img_bytes,
                filename="upload.jpg",
                max_file_size_mb=self.settings.image_captioning_max_file_size_mb,
                allowed_formats=self.settings.image_captioning_allowed_formats,
            )
            processed_img = self.image_service.process_image(
                content_bytes=raw_img_bytes,
                filename="upload.jpg",
                max_dimension=1024,
            )

            # Persist optimized file in user isolated directory
            saved_image_path = self.image_service.save_image(
                content_bytes=processed_img.processed_bytes,
                original_filename="upload.jpg",
                user_id=user_id,
            )

            # Extract narrative vision cues
            visual_context = await self.agent_pipeline.extract_visual_context(
                prompt=req.prompt,
                content_type=content_type,
                image_base64=processed_img.base64_str,
                mime_type=processed_img.mime_type,
            )

        # 4. Content Strategist & Planner Step
        plan_breakdown = await self.agent_pipeline.generate_plan(
            content_type=content_type,
            prompt=req.prompt,
            profile=profile,
            visual_context=visual_context,
            few_shot_examples=few_shot_examples,
        )

        # 5. Personalized Generator & Reviewer Step
        generated_content = await self.agent_pipeline.generate_content(
            content_type=content_type,
            prompt=req.prompt,
            profile=profile,
            plan_breakdown=plan_breakdown,
            visual_context=visual_context,
            few_shot_examples=few_shot_examples,
        )

        elapsed = round(time.perf_counter() - start_time, 3)

        decision_chain = self._build_decision_chain(
            profile=profile,
            content_type=content_type,
            few_shot_examples=few_shot_examples,
            visual_context=visual_context,
            plan_breakdown=plan_breakdown,
            generated_content=generated_content,
            elapsed=elapsed,
        )

        return ContentGenerationResponse(
            id=str(uuid.uuid4()),
            content_type=content_type,
            prompt=req.prompt,
            generated_content=generated_content,
            plan_breakdown=plan_breakdown,
            image_path=saved_image_path,
            decision_chain=decision_chain,
            visual_context_used=bool(visual_context),
            few_shot_examples_count=len(few_shot_examples),
            execution_time=elapsed,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _build_decision_chain(
        self,
        profile: dict[str, Any],
        content_type: str,
        few_shot_examples: list[dict[str, Any]],
        visual_context: str,
        plan_breakdown: str,
        generated_content: str,
        elapsed: float,
    ) -> list[dict[str, Any]]:
        """Construct the 5-stage decision chain trace for the response payload."""
        hobbies_list = profile.get("hobbies") or profile.get("interests") or []
        hobbies_display = (
            ", ".join(hobbies_list) if isinstance(hobbies_list, list) else str(hobbies_list)
        )
        word_count = len(generated_content.split())
        char_count = len(generated_content)

        vis_details = (
            f"Extracted visual features & narrative cues:\n\n{visual_context.strip()}"
            if visual_context
            else "Skipped — No multimodal image attachment provided."
        )
        plan_details = (
            f"Synthesized editorial strategy for {content_type}:\n\n{plan_breakdown.strip()}"
        )
        writer_details = (
            f"Generated {word_count} words ({char_count} chars) in "
            f"{profile.get('preferred_language', 'English')}. "
            f"Embodied {profile.get('gender', 'Male')} author "
            f"(Age: {profile.get('age', 30)}) with grounded bio facts. "
            "Editorial review passed."
        )

        return [
            {
                "stage": "1. 👤 Profile & Persona Calibration",
                "details": (
                    f"Author: {profile.get('username', 'Author')} | "
                    f"Role: {profile.get('profession', 'Professional')} "
                    f"({profile.get('industry', 'General')}) | "
                    f"Age: {profile.get('age', 30)} | Gender: {profile.get('gender', 'Male')} | "
                    f"Language: {profile.get('preferred_language', 'English')} | "
                    f"Hobbies: {hobbies_display or 'None'}"
                ),
            },
            {
                "stage": "2. 🧠 Few-Shot Personalization Retrieval (ChromaDB)",
                "details": (
                    f"Retrieved {len(few_shot_examples)} exemplars as few-shot style anchors "
                    "from user vector store."
                    if few_shot_examples
                    else "No personalized style exemplars found or RAG retrieval skipped."
                ),
                "samples": [
                    {"title": ex.get("title", ""), "tags": ex.get("tags", [])}
                    for ex in few_shot_examples
                ],
            },
            {
                "stage": "3. 🖼️ Multimodal Vision Extraction",
                "details": vis_details,
            },
            {
                "stage": "4. 📋 Editorial Strategy & Outlining (Planner Agent)",
                "details": plan_details,
            },
            {
                "stage": "5. ✨ Tone Calibration & Generation (Writer Agent)",
                "details": writer_details,
            },
        ]

    # -------------------------------------------------------------------------
    # Content History & Feedback
    # -------------------------------------------------------------------------

    async def get_history(self, user_id: str, limit: int = 20) -> list[ContentHistoryItem]:
        """Fetch user content history (published / submitted posts)."""
        items = self.user_repo.get_content_history(user_id, limit=limit)
        return [ContentHistoryItem(**item) for item in items]

    async def submit_post(
        self, user_id: str, req: ContentSubmitRequest
    ) -> ContentHistoryItem:
        """Persist a submitted post to SQLite history and optionally index into personal dataset."""
        history_item = self.user_repo.save_content_history(
            user_id=user_id,
            content_type=req.content_type,
            prompt=req.prompt,
            generated_content=req.generated_content,
            plan_breakdown=req.plan_breakdown,
            image_path=req.image_path,
        )

        result = self.user_repo.update_content_feedback(
            history_id=history_item["id"],
            user_id=user_id,
            rating=req.rating,
            save_to_dataset=req.save_to_dataset,
        )

        if req.save_to_dataset and req.rating >= 4:
            title = (
                f"{result['content_type'].replace('_', ' ').title()} "
                f"on {result['prompt'][:30]}..."
            )
            self.user_repo.save_writing_sample(
                user_id=user_id,
                title=title,
                content_type=result["content_type"],
                content=result["generated_content"],
                tags=["user_liked", result["content_type"]],
                sample_id=result["id"],
            )
            self.dataset_service.index_vector_sample(
                sample_id=result["id"],
                user_id=user_id,
                title=title,
                content_type=result["content_type"],
                content=result["generated_content"],
                tags=["user_liked", result["content_type"]],
            )

        return ContentHistoryItem(**result)

    async def submit_feedback(
        self, user_id: str, req: ContentFeedbackRequest
    ) -> dict[str, Any]:
        """Legacy feedback endpoint for rating existing history items."""
        history_items = self.user_repo.get_content_history(user_id, limit=50)
        existing = next((h for h in history_items if h["id"] == req.history_id), None)
        already_saved = bool(existing.get("saved_to_dataset")) if existing else False

        result = self.user_repo.update_content_feedback(
            history_id=req.history_id,
            user_id=user_id,
            rating=req.rating,
            save_to_dataset=req.save_to_dataset,
        )

        if not already_saved and req.save_to_dataset and req.rating >= 4:
            title = (
                f"{result['content_type'].replace('_', ' ').title()} "
                f"on {result['prompt'][:30]}..."
            )
            self.dataset_service.index_vector_sample(
                sample_id=result["id"],
                user_id=user_id,
                title=title,
                content_type=result["content_type"],
                content=result["generated_content"],
                tags=["user_liked", result["content_type"]],
            )

        return result
