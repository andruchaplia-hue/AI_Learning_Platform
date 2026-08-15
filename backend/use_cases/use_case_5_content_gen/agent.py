import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from backend.domain.exceptions import ConfigurationError, ProviderError
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base_provider import FrameworkType

logger = logging.getLogger(__name__)


def _load_prompt(filename: str) -> str:
    path = Path(__file__).resolve().parent / "prompts" / filename
    if not path.exists():
        raise ConfigurationError(f"Prompt template file not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_format_prompt(content_type: str) -> str:
    """Load dedicated formatting rules file for specific content type."""
    normalized_type = str(content_type).lower().strip().replace(" ", "_")
    path = Path(__file__).resolve().parent / "prompts" / "formats" / f"{normalized_type}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return f"[FORMATTING RULES FOR {content_type.upper()}]\nWrite clear, structured, and authentic content for this format."


def _get_planner_format_instructions(content_type: str) -> str:
    """Provide tailored planning outline instructions based on content type."""
    normalized_type = str(content_type).lower().strip().replace(" ", "_")
    if normalized_type == "social_media_post":
        return "- For Social Media Post: Provide strictly 1 single sentence core idea/hook and tone note (no long multi-section outline)."
    return "- Develop a concise editorial strategy: 1. Core Hook, 2. Key Section Points (3-5 bullets), 3. Tone Calibration Notes, 4. Recommended CTA."


class ContentAgentPipeline:
    """Multi-step LangChain LCEL agent pipeline (Planner -> Generator -> Reviewer)."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.llm = LLMGateway.get_llm(settings, framework=FrameworkType.LANGCHAIN)

        # Load prompts
        self.planner_prompt_template = _load_prompt("planner_prompt.txt")
        self.generator_prompt_template = _load_prompt("generator_prompt.txt")
        self.vision_prompt_template = _load_prompt("vision_extractor_prompt.txt")

        # Build LCEL chains
        planner_prompt = ChatPromptTemplate.from_template(self.planner_prompt_template)
        generator_prompt = ChatPromptTemplate.from_template(self.generator_prompt_template)
        parser = StrOutputParser()

        self.planner_chain = planner_prompt | self.llm | parser
        self.generator_chain = generator_prompt | self.llm | parser

    async def extract_visual_context(
        self, prompt: str, content_type: str, image_base64: str, mime_type: str = "image/jpeg"
    ) -> str:
        """Analyze image and extract narrative visual context for the content generation task."""
        try:
            instruction = self.vision_prompt_template.format(
                prompt=prompt, content_type=content_type
            )
            messages = [
                SystemMessage(content="You are an expert multimodal visual analyst for content creation."),
                HumanMessage(
                    content=[
                        {"type": "text", "text": instruction},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                        },
                    ]
                ),
            ]
            response = await self.llm.ainvoke(messages)
            raw_content = response.content if hasattr(response, "content") else response
            return self._sanitize_extracted_text(raw_content)
        except Exception as exc:
            logger.error(f"Visual context extraction failed: {exc}", exc_info=True)
            raise ProviderError(f"Failed to process visual context from image: {exc}") from exc

    def _sanitize_extracted_text(self, raw_content: Any) -> str:
        """Sanitize response content into clean text, stripping dictionary artifacts or model signatures."""
        if isinstance(raw_content, str):
            text = raw_content
        elif isinstance(raw_content, list):
            text_parts = []
            for item in raw_content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    if item.get("type") == "text" and "text" in item:
                        text_parts.append(item["text"])
                    elif "text" in item:
                        text_parts.append(str(item["text"]))
            text = "\n".join(text_parts) if text_parts else str(raw_content)
        elif isinstance(raw_content, dict):
            text = raw_content.get("text", "") or str(raw_content)
        else:
            text = str(raw_content)

        # Remove trailing signature / extras or python dict representations if present
        cleaned_lines = []
        for line in text.splitlines():
            line_strip = line.strip()
            # Filter out line if it looks like an extras/signature dict dump
            if (
                line_strip.startswith("{'extras':")
                or line_strip.startswith("{\"extras\":")
                or "'signature':" in line_strip
                or '"signature":' in line_strip
            ):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    async def generate_plan(
        self,
        content_type: str,
        prompt: str,
        profile: dict[str, Any],
        visual_context: str = "",
        few_shot_examples: list[dict[str, Any]] | None = None,
    ) -> str:
        """Step 1: Content Strategist & Outline Planning."""
        visual_section = (
            f"[VISUAL CONTEXT FROM ATTACHED IMAGE]\n{visual_context}" if visual_context else ""
        )
        few_shot_section = self._format_few_shot_section(few_shot_examples or [])
        planner_format = _get_planner_format_instructions(content_type)
        hobbies_val = profile.get("hobbies") or profile.get("interests") or []
        hobbies_str = ", ".join(hobbies_val) if isinstance(hobbies_val, list) else str(hobbies_val)
        bio_str = profile.get("bio") or profile.get("style_notes") or ""
        age_val = profile.get("age") or 30
        gender_val = profile.get("gender") or "Male"

        try:
            plan = await self.planner_chain.ainvoke(
                {
                    "content_type": content_type,
                    "preferred_language": profile.get("preferred_language", "English"),
                    "prompt": prompt,
                    "username": profile.get("username", "Author"),
                    "profession": profile.get("profession", "Professional"),
                    "industry": profile.get("industry", "General"),
                    "age": age_val,
                    "gender": gender_val,
                    "hobbies": hobbies_str,
                    "bio": bio_str,
                    "visual_context_section": visual_section,
                    "few_shot_section": few_shot_section,
                    "format_instructions": planner_format,
                }
            )
            return str(plan).strip()
        except Exception as exc:
            logger.error(f"Content planning step failed: {exc}", exc_info=True)
            raise ProviderError(f"Content planning step failed: {exc}") from exc

    async def generate_content(
        self,
        content_type: str,
        prompt: str,
        profile: dict[str, Any],
        plan_breakdown: str,
        visual_context: str = "",
        few_shot_examples: list[dict[str, Any]] | None = None,
    ) -> str:
        """Step 2: Personalized Content Generation and Polish Review."""
        visual_section = (
            f"[VISUAL CONTEXT FROM ATTACHED IMAGE]\n{visual_context}" if visual_context else ""
        )
        few_shot_section = self._format_few_shot_section(few_shot_examples or [])
        format_rules = _load_format_prompt(content_type)
        hobbies_val = profile.get("hobbies") or profile.get("interests") or []
        hobbies_str = ", ".join(hobbies_val) if isinstance(hobbies_val, list) else str(hobbies_val)
        bio_str = profile.get("bio") or profile.get("style_notes") or ""
        age_val = profile.get("age") or 30
        gender_val = profile.get("gender") or "Male"

        try:
            content = await self.generator_chain.ainvoke(
                {
                    "content_type": content_type,
                    "preferred_language": profile.get("preferred_language", "English"),
                    "prompt": prompt,
                    "username": profile.get("username", "Author"),
                    "profession": profile.get("profession", "Professional"),
                    "industry": profile.get("industry", "General"),
                    "age": age_val,
                    "gender": gender_val,
                    "hobbies": hobbies_str,
                    "bio": bio_str,
                    "visual_context_section": visual_section,
                    "few_shot_section": few_shot_section,
                    "plan_breakdown": plan_breakdown,
                    "format_instructions": format_rules,
                }
            )
            return str(content).strip()
        except Exception as exc:
            logger.error(f"Content generation step failed: {exc}", exc_info=True)
            raise ProviderError(f"Content generation step failed: {exc}") from exc

    def _format_few_shot_section(self, examples: list[dict[str, Any]]) -> str:
        if not examples:
            return ""
        lines = ["[AUTHOR'S PERSONAL WRITING EXAMPLES (FEW-SHOT TONE & STYLE ANCHORS)]"]
        for idx, ex in enumerate(examples, 1):
            title = ex.get("title", f"Example {idx}")
            body = ex.get("content", "")
            lines.append(f"--- Example #{idx}: {title} ---")
            lines.append(body)
        lines.append("--- End of Examples ---")
        return "\n".join(lines)
