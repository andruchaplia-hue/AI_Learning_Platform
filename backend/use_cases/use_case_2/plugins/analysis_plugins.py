import json
import logging
import re
from typing import Any

from backend.infrastructure.config.settings import AppSettings
from backend.use_cases.use_case_2.models import RetrievedFAQ
from backend.use_cases.use_case_2.prompt_loader import load_prompt
from backend.infrastructure.llm.compat import kernel_function

logger = logging.getLogger(__name__)


def _extract_text_content(content: Any) -> str:
    """Safely extract plain text from LangChain message content blocks (Gemini can return lists)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif hasattr(part, "text"):
                parts.append(part.text)
            elif isinstance(part, str):
                parts.append(part)
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)


class QueryDecomposerPlugin:
    """Semantic Kernel Plugin for splitting compound queries into independent sub-questions."""

    def __init__(self, settings: AppSettings, llm: Any = None):
        self.settings = settings
        self.llm = llm

    @kernel_function(
        name="decompose_query",
        description="Decompose a compound user question into a JSON list of independent questions."
    )
    async def decompose_query(self, query: str) -> str:
        """Decompose a compound query using LLM (if google) or rule-based fallback (if mock)."""
        logger.info(f"QueryDecomposerPlugin: decomposing query: '{query}'")
        cleaned = query.strip()
        if not cleaned:
            return json.dumps({"questions": []})

        # Check if provider is mock or LLM is not provided
        if self.settings.provider.lower().strip() == "mock" or not self.settings.google_api_key or not self.llm:
            # Rule-based split on sentence boundaries or explicit separators
            raw_parts = re.split(r'\?+|\n+|(?:^|\s+)(?:and|also|plus|as well as)\s+', cleaned, flags=re.IGNORECASE)
            sub_qs = [p.strip() for p in raw_parts if len(p.strip()) > 3]
            formatted_qs = [q if q.endswith("?") else f"{q}?" for q in sub_qs]
            if not formatted_qs:
                formatted_qs = [cleaned if cleaned.endswith("?") else f"{cleaned}?"]
            return json.dumps({"questions": formatted_qs}, ensure_ascii=False)

        # Call live Google Gemini model to split compound query
        try:
            template = load_prompt("decomposition_prompt.txt")
            prompt = template.replace("{query}", cleaned)
            response = await self.llm.ainvoke(prompt) if hasattr(self.llm, "ainvoke") else self.llm.invoke(prompt)

            raw_content = response.content if hasattr(response, "content") else response
            raw_response = _extract_text_content(raw_content)

            # Strip code blocks
            clean_json = re.sub(r"```(?:json)?|```", "", raw_response).strip()
            parsed = json.loads(clean_json)
            if isinstance(parsed, dict) and "questions" in parsed:
                return json.dumps(parsed, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"Query decomposition LLM failed: {exc}. Falling back to rule-based parser.")

        # Fallback if LLM failed
        raw_parts = re.split(r'\?+|\n+|(?:^|\s+)(?:and|also|plus|as well as)\s+', cleaned, flags=re.IGNORECASE)
        sub_qs = [p.strip() for p in raw_parts if len(p.strip()) > 3]
        formatted_qs = [q if q.endswith("?") else f"{q}?" for q in sub_qs]
        if not formatted_qs:
            formatted_qs = [cleaned if cleaned.endswith("?") else f"{cleaned}?"]
        return json.dumps({"questions": formatted_qs}, ensure_ascii=False)


class CoverageAnalyzerPlugin:
    """Semantic Kernel Plugin for evaluating question coverage using LLM prompt evaluation."""

    def __init__(self, settings: AppSettings, llm: Any = None):
        self.settings = settings
        self.llm = llm

    @kernel_function(
        name="analyze_coverage",
        description="Verify search result coverage for each decomposed sub-question using LLM reasoning."
    )
    async def analyze_coverage(self, sub_questions_json: str, retrieved_faqs_json: str) -> str:
        """Evaluate how well the retrieved FAQs cover the decomposed sub-questions using LLM reasoning."""
        logger.info("CoverageAnalyzerPlugin: analyzing search coverage using LLM...")
        try:
            sub_qs = json.loads(sub_questions_json).get("questions", [])
        except Exception:
            sub_qs = []

        try:
            retrieved = json.loads(retrieved_faqs_json)
        except Exception:
            retrieved = []

        if not sub_qs:
            return json.dumps({"coverage_score": 0.0, "covered_questions": [], "missing_questions": []})

        if not retrieved:
            return json.dumps({"coverage_score": 0.0, "covered_questions": [], "missing_questions": sub_qs})

        # LLM-based coverage evaluation
        try:
            if not self.llm or self.settings.provider.lower().strip() == "mock" or not self.settings.google_api_key:
                raise ValueError("LLM not available or mock provider active.")

            template = load_prompt("coverage_prompt.txt")
            prompt = template.replace("{sub_questions_json}", sub_questions_json)\
                             .replace("{retrieved_faqs_json}", retrieved_faqs_json)

            response = await self.llm.ainvoke(prompt) if hasattr(self.llm, "ainvoke") else self.llm.invoke(prompt)
            raw_content = response.content if hasattr(response, "content") else response
            raw_response = _extract_text_content(raw_content)

            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                clean_json = json_match.group(0).strip()
            else:
                clean_json = re.sub(r"```(?:json)?|```", "", raw_response).strip()

            parsed = json.loads(clean_json)
            if "coverage_score" in parsed and "missing_questions" in parsed:
                # Ensure selected_faq_ids exists in parsed output
                if "selected_faq_ids" not in parsed:
                    parsed["selected_faq_ids"] = []
                return json.dumps(parsed, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"CoverageAnalyzerPlugin LLM evaluation failed: {exc}")

        # Fallback when LLM is unavailable: do not block response, return 1.0 coverage and empty selected_faq_ids
        return json.dumps({
            "coverage_score": 1.0,
            "covered_questions": sub_qs,
            "missing_questions": [],
            "selected_faq_ids": []
        }, ensure_ascii=False)
