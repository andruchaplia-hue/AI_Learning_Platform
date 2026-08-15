import json
import logging
from pathlib import Path
from typing import Any

from backend.domain.exceptions import ProviderError
from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base_provider import FrameworkType
from backend.use_cases.use_case_4_code_generation.models import DatasetEntry
from backend.use_cases.use_case_4_code_generation.plugins import (
    CodeGeneratorPlugin,
    CodeReviewerPlugin,
    ImprovementAdvisorPlugin,
    RequirementsAnalyzerPlugin,
)

logger = logging.getLogger(__name__)


class CodeGenerationAgent:
    """Semantic Kernel AI Agent orchestrating sequential plugin pipeline for code generation and review."""

    def __init__(self, settings: AppSettings, model_name: str | None = None):
        self.settings = settings
        self.model_name = model_name or settings.google_model
        self.analyzer_plugin = RequirementsAnalyzerPlugin(settings)
        self.generator_plugin = CodeGeneratorPlugin(settings)
        self.reviewer_plugin = CodeReviewerPlugin(settings)
        self.advisor_plugin = ImprovementAdvisorPlugin(settings)

        # Get Semantic Kernel object from gateway
        provider = LLMGateway.get_provider(settings, model_name=self.model_name)
        self._kernel = provider.get_llm(framework=FrameworkType.SEMANTIC_KERNEL)

        # Register plugins if kernel supports add_plugin
        if hasattr(self._kernel, "add_plugin"):
            self._kernel.add_plugin(self.analyzer_plugin, plugin_name="RequirementsAnalyzerPlugin")
            self._kernel.add_plugin(self.generator_plugin, plugin_name="CodeGeneratorPlugin")
            self._kernel.add_plugin(self.reviewer_plugin, plugin_name="CodeReviewerPlugin")
            self._kernel.add_plugin(self.advisor_plugin, plugin_name="ImprovementAdvisorPlugin")

    def _load_prompt_template(self, name: str) -> str:
        prompt_dir = Path(__file__).resolve().parent / "prompts"
        prompt_file = prompt_dir / f"{name}.txt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return ""

    async def _invoke_llm(self, prompt_name: str, **kwargs: str) -> str:
        """Invoke SK prompt function or fallback to LangChain LLM from Gateway."""
        template = self._load_prompt_template(prompt_name)
        prompt = template
        for k, v in kwargs.items():
            prompt = prompt.replace(f"{{{{ ${k} }}}}", str(v))

        kernel = self._kernel

        # 1. Attempt Semantic Kernel prompt function invocation
        if hasattr(kernel, "add_function"):
            try:
                sk_func = kernel.add_function(
                    function_name=f"exec_{prompt_name}",
                    plugin_name="CodeGenPlugin",
                    prompt=prompt,
                )
                result = await kernel.invoke(sk_func)
                res_val = getattr(result, "value", result)
                if isinstance(res_val, list):
                    res_str = "\n".join(str(item) for item in res_val if item).strip()
                else:
                    res_str = str(res_val).strip()

                if res_str:
                    return res_str
            except Exception as exc:
                logger.warning(f"Semantic Kernel prompt invocation failed for {prompt_name} ({exc}). Retrying via Gateway LLM...")

        # 2. Dynamic fallback using requested model from LLMGateway
        try:
            lc_llm = LLMGateway.get_llm(self.settings, framework=FrameworkType.LANGCHAIN, model_name=self.model_name)
            response = await lc_llm.ainvoke(prompt) if hasattr(lc_llm, "ainvoke") else lc_llm.invoke(prompt)
            res_content = response.content if hasattr(response, "content") else str(response)
            if isinstance(res_content, list):
                res_str = "\n".join(str(item.get("text", item) if isinstance(item, dict) else item) for item in res_content if item)
            else:
                res_str = str(res_content)
            return res_str.strip()
        except Exception as exc:
            logger.error(f"Gateway LLM invocation failed for {prompt_name}: {exc}", exc_info=True)
            raise ProviderError(f"LLM model generation failed for stage '{prompt_name}': {exc}") from exc

    @staticmethod
    def _format_few_shot_block(examples: list[DatasetEntry]) -> str:
        """Format DatasetEntry list into a numbered few-shot reference block for prompt injection."""
        if not examples:
            return ""
        lines: list[str] = []
        for i, ex in enumerate(examples, 1):
            lines.append(f"[Example {i}]")
            lines.append(f"User: {ex.user_prompt}")
            lines.append(f"Code:\n{ex.expected_code}")
            lines.append("")
        return "\n".join(lines).strip()

    async def run_pipeline(
        self,
        prompt: str,
        target_content: str = "",
        few_shot_examples: list[DatasetEntry] | None = None,
    ) -> tuple[str, dict[str, Any], str, list[str]]:
        """Run 4-stage sequential agent pipeline with optional RAG few-shot context.

        Args:
            prompt: Natural language code generation request.
            target_content: Optional existing file content for contextual refactoring.
            few_shot_examples: Optional list of DatasetEntry objects retrieved via RAG.
                               When provided, they are formatted and injected into the
                               Code Generator prompt as few-shot reference examples.
        """
        logger.info(
            f"CodeGenerationAgent executing SK pipeline for model: '{self.model_name}' "
            f"| few_shot_examples: {len(few_shot_examples) if few_shot_examples else 0}"
        )

        # Stage 1: Requirements Analysis
        req_prompt_res = await self._invoke_llm(
            "analyzer", prompt=prompt, target_content=target_content
        )
        try:
            # Clean JSON formatting if LLM wrapped in markdown blocks
            clean_json = req_prompt_res
            if clean_json.startswith("```"):
                lines = clean_json.splitlines()
                if len(lines) >= 2 and lines[-1].startswith("```"):
                    clean_json = "\n".join(lines[1:-1])
                if clean_json.startswith("json"):
                    clean_json = clean_json[4:].strip()
            requirements_dict = json.loads(clean_json)
        except Exception:
            requirements_dict = {
                "language": "python",
                "framework": "standard",
                "key_functions": ["main"],
                "constraints": ["PEP8"],
                "prompt": prompt,
            }

        # Stage 2: Code Generation  (inject RAG few-shot context when available)
        few_shot_block = self._format_few_shot_block(few_shot_examples or [])
        generated_code = await self._invoke_llm(
            "generator",
            prompt=prompt,
            requirements=json.dumps(requirements_dict),
            target_content=target_content,
            few_shot_context=few_shot_block,
        )
        # Strip markdown ```python code fences if present
        if generated_code.startswith("```"):
            lines = generated_code.splitlines()
            if len(lines) >= 2 and lines[-1].startswith("```"):
                first_line = lines[0].lower().strip()
                if first_line.startswith("```python") or first_line == "```":
                    generated_code = "\n".join(lines[1:-1])

        # Stage 3: Code Review
        review_comments = await self._invoke_llm(
            "reviewer", code=generated_code, prompt=prompt
        )

        # Stage 4: Improvement Suggestions
        advisor_str = await self._invoke_llm(
            "advisor", code=generated_code, review=review_comments
        )
        suggestions = [
            line.lstrip("-* ").strip()
            for line in advisor_str.splitlines()
            if line.strip().startswith(("-", "*"))
        ]
        if not suggestions:
            suggestions = [
                "Add type annotations for input parameters and return values.",
                "Add docstrings to explain function behavior.",
                "Provide unit test coverage for edge cases.",
            ]

        return generated_code, requirements_dict, review_comments, suggestions
