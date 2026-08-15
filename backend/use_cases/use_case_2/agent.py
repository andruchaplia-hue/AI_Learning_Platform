import json
import logging
from typing import Any

from backend.domain.exceptions import ProviderError
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base_provider import FrameworkType
from backend.use_cases.use_case_2.plugins.faq_plugin import FAQPlugin
from backend.use_cases.use_case_2.plugins.analysis_plugins import QueryDecomposerPlugin, CoverageAnalyzerPlugin
from backend.use_cases.use_case_2.models import RetrievedFAQ

from semantic_kernel.functions import KernelArguments
from backend.use_cases.use_case_2.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class FAQAgent:
    """Semantic Kernel AI Agent for answering FAQ queries with strict RAG grounding, tool calling, and analysis plugins."""

    def __init__(self, settings: AppSettings, faq_plugin: FAQPlugin):
        self.settings = settings
        self.faq_plugin = faq_plugin
        self.provider_name = settings.provider.lower().strip()

        # Instantiate provider and LLMs once at construction time
        provider = LLMGateway.get_provider(settings)
        self._kernel = provider.get_llm(framework=FrameworkType.SEMANTIC_KERNEL)
        self._lc_llm = provider.get_llm(framework=FrameworkType.LANGCHAIN)

        self.decomposer_plugin = QueryDecomposerPlugin(settings, llm=self._lc_llm)
        self.coverage_plugin = CoverageAnalyzerPlugin(settings, llm=self._lc_llm)

        # Register plugins if this is a real SK Kernel object
        if hasattr(self._kernel, "add_plugin"):
            self._kernel.add_plugin(faq_plugin, plugin_name="FAQPlugin")
            self._kernel.add_plugin(self.decomposer_plugin, plugin_name="DecomposerPlugin")
            self._kernel.add_plugin(self.coverage_plugin, plugin_name="CoveragePlugin")

    def _is_sk_kernel(self) -> bool:
        """Return True if the cached kernel is a real Semantic Kernel Kernel object."""
        return hasattr(self._kernel, "add_plugin")

    async def _invoke_sk_function(self, plugin_name: str, function_name: str, **kwargs) -> str:
        """Invoke a registered SK plugin function by name; fall back to direct plugin call if not SK."""
        kernel = self._kernel
        if self._is_sk_kernel():
            func = kernel.get_function(plugin_name, function_name)
            args = KernelArguments(**kwargs)
            result = await kernel.invoke(func, args)
            return str(result)
        # Fallback: call plugin method directly
        plugin_obj = getattr(self, f"{plugin_name.lower().replace('plugin', '_plugin').rstrip('_')}_plugin",
                             self.faq_plugin)
        method = getattr(plugin_obj, function_name)
        result = method(**kwargs) if not hasattr(method, "__wrapped__") else await method(**kwargs)
        return result if isinstance(result, str) else str(result)

    async def _decompose_query(self, query: str) -> tuple[list[str], bool, str]:
        """Decompose compound query into sub-questions."""
        decomposer_fallback = False
        try:
            if self._is_sk_kernel():
                decomp_json = await self._invoke_sk_function("DecomposerPlugin", "decompose_query", query=query)
            else:
                decomp_json = await self.decomposer_plugin.decompose_query(query)

            sub_qs = json.loads(decomp_json).get("questions", [])
        except Exception as exc:
            logger.error(f"Decomposer plugin execution failed, falling back to original query: {exc}", exc_info=True)
            decomposer_fallback = True
            sub_qs = [query]
            decomp_json = json.dumps({"questions": sub_qs})
        return sub_qs, decomposer_fallback, decomp_json

    async def _retrieve_candidates(self, sub_qs: list[str]) -> list[RetrievedFAQ]:
        """Retrieve matching FAQs for each sub-question."""
        all_retrieved: list[RetrievedFAQ] = []
        retrieved_ids = set()

        for q in sub_qs:
            if self._is_sk_kernel():
                raw_res = await self._invoke_sk_function("FAQPlugin", "search_faq", query=q)
            else:
                raw_res = self.faq_plugin.search_faq(q)

            try:
                parsed = json.loads(raw_res)
                if parsed.get("status") == "success":
                    for item in parsed.get("results", []):
                        if item["id"] not in retrieved_ids:
                            retrieved_ids.add(item["id"])
                            all_retrieved.append(
                                RetrievedFAQ(
                                    id=item["id"],
                                    category=item["category"],
                                    question=item["question"],
                                    answer=item["answer"],
                                    score=item["similarity_score"],
                                )
                            )
            except Exception as exc:
                logger.error(f"Error parsing search results for query '{q}': {exc}", exc_info=True)
        return all_retrieved

    async def _analyze_coverage(
        self, decomp_json: str, sub_qs: list[str], all_retrieved: list[RetrievedFAQ]
    ) -> tuple[float, list[int], list[str], bool, str | None]:
        """Evaluate retrieval coverage against decomposed sub-questions."""
        retrieved_json = json.dumps([
            {
                "id": r.id,
                "question": r.question,
                "answer": r.answer,
                "similarity_score": r.score,
            } for r in all_retrieved
        ], ensure_ascii=False)

        coverage_fallback = False
        pipeline_error = None
        try:
            if self._is_sk_kernel():
                cov_str = await self._invoke_sk_function(
                    "CoveragePlugin", "analyze_coverage",
                    sub_questions_json=decomp_json, retrieved_faqs_json=retrieved_json
                )
                cov_report = json.loads(cov_str)
            else:
                cov_report = json.loads(await self.coverage_plugin.analyze_coverage(decomp_json, retrieved_json))

        except Exception as exc:
            logger.error(f"Coverage plugin execution failed, bypassing coverage validation: {exc}", exc_info=True)
            coverage_fallback = True
            pipeline_error = str(exc)
            cov_report = {"coverage_score": 1.0, "covered_questions": sub_qs, "missing_questions": [], "selected_faq_ids": []}

        coverage_score = cov_report.get("coverage_score", 1.0)
        selected_ids = cov_report.get("selected_faq_ids", [])
        missing_questions = cov_report.get("missing_questions", [])
        return coverage_score, selected_ids, missing_questions, coverage_fallback, pipeline_error

    async def _synthesize_answer(
        self, query: str, sub_qs: list[str], valid_faqs: list[RetrievedFAQ], chat_history: list[dict[str, str]] | None
    ) -> str:
        """Synthesize a single consolidated user-friendly response using LLM."""
        formatted_context = "\n---\n".join([
            f"[FAQ #{f.id}] Category: {f.category}\nQuestion: {f.question}\nAnswer: {f.answer}"
            for f in valid_faqs
        ])

        history_str = ""
        if chat_history:
            history_str = "\nRecent History:\n" + "\n".join([
                f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history[-4:]
            ])

        system_prompt = load_prompt("system_prompt.txt")
        synthesis_template = load_prompt("answer_synthesis_prompt.txt")

        sub_q_str = "\n".join([f"- {q}" for q in sub_qs])
        prompt_template = synthesis_template.replace("{system_prompt}", system_prompt)\
                                            .replace("{history_str}", history_str)\
                                            .replace("{sub_q_str}", sub_q_str)\
                                            .replace("{formatted_context}", formatted_context)\
                                            .replace("{query}", query)

        logger.info(f"=== FAQAgent SK Prompt Payload ===\n{prompt_template}\n==================================")

        kernel = self._kernel
        if hasattr(kernel, "add_function"):
            req_settings = None
            try:
                req_settings = kernel.get_service().instantiate_prompt_execution_settings()
                try:
                    req_settings.temperature = self.settings.temperature
                except Exception:
                    pass
                try:
                    if hasattr(req_settings, "max_output_tokens"):
                        req_settings.max_output_tokens = self.settings.max_tokens
                    elif hasattr(req_settings, "max_tokens"):
                        req_settings.max_tokens = self.settings.max_tokens
                except Exception:
                    pass
            except Exception:
                req_settings = None

            sk_func = kernel.add_function(
                function_name="answer_faq",
                plugin_name="FAQPlugin",
                prompt=prompt_template
            )
            result = await kernel.invoke(sk_func)
            answer_text = str(result)
        else:
            response = await kernel.ainvoke(prompt_template) if hasattr(kernel, "ainvoke") else kernel.invoke(prompt_template)
            answer_text = response.content if hasattr(response, "content") else str(response)

        return answer_text.strip()

    async def invoke(
        self,
        query: str,
        chat_history: list[dict[str, str]] | None = None,
        user_friendly: bool = True,
        sk_filtering: bool = True,
    ) -> tuple[str, list[RetrievedFAQ], bool, dict[str, Any]]:
        """Invoke agent pipeline.

        Returns:
            tuple of (synthesized_answer_text, retrieved_faqs, is_found, inspection_metrics_dict)
        """
        logger.info(f"FAQAgent orchestrating pipeline for query: '{query}' (user_friendly={user_friendly}, sk_filtering={sk_filtering})")

        # Step 1: Decompose query
        sub_qs, decomposer_fallback, decomp_json = await self._decompose_query(query)

        # Step 2: Retrieve candidates
        all_retrieved = await self._retrieve_candidates(sub_qs)

        # Step 3: Analyze coverage
        coverage_score, selected_ids, missing_questions, coverage_fallback, pipeline_error = await self._analyze_coverage(
            decomp_json, sub_qs, all_retrieved
        )

        # Step 4: Evaluate and Filter FAQs
        valid_faqs = [f for f in all_retrieved if f.score >= self.settings.faq_similarity_threshold]

        # Apply SK Agent selection filter if enabled and selected_ids is populated
        if sk_filtering and selected_ids:
            valid_faqs = [f for f in valid_faqs if f.id in selected_ids]

        # Build inspection details metrics dictionary
        max_score = max([f.score for f in all_retrieved], default=0.0)
        inspection_metrics = {
            "decomposed_queries": sub_qs,
            "retrieved_faqs": all_retrieved,
            "max_similarity_score": round(max_score, 4),
            "coverage_score": coverage_score,
            "missing_questions": missing_questions,
            "user_friendly": user_friendly,
            "sk_filtering": sk_filtering,
            "selected_faq_ids": selected_ids,
            "decomposer_fallback": decomposer_fallback,
            "coverage_fallback": coverage_fallback,
            "pipeline_error": pipeline_error,
            "is_fallback": False
        }

        # Check Rule 1 & Rule 2: If coverage is 0.0 or no valid FAQs found, block response and trigger fallback
        if coverage_score == 0.0 or not valid_faqs:
            fallback_answer = (
                "Unfortunately, no suitable answer was found in our knowledge base for your question. "
                "Please contact customer support at support@platform.com."
            )
            inspection_metrics["is_fallback"] = True
            return fallback_answer, all_retrieved, False, inspection_metrics

        # If user_friendly is False, return direct raw FAQ answers without LLM synthesis
        if not user_friendly:
            raw_answers = []
            for idx, f in enumerate(valid_faqs, 1):
                raw_answers.append(f"**[FAQ #{f.id}] {f.question}**\n{f.answer}")
            direct_answer = "\n\n".join(raw_answers)
            return direct_answer, valid_faqs, True, inspection_metrics

        # Step 5: Response Synthesis
        try:
            answer_text = await self._synthesize_answer(query, sub_qs, valid_faqs, chat_history)
            return answer_text, valid_faqs, True, inspection_metrics
        except Exception as exc:
            logger.error(f"FAQAgent SK generation failed: {exc}", exc_info=True)
            raise ProviderError(f"LLM synthesis failed: {exc}") from exc
