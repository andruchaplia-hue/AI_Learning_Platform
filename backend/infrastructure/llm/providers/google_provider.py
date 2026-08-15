from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from backend.domain.exceptions import ConfigurationError, ProviderError
from backend.infrastructure.llm.providers.base_provider import BaseProvider, FrameworkType


class GoogleProvider(BaseProvider):
    """Google Gemini LLM provider implementation supporting multiple target frameworks."""

    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> None:
        if not api_key or api_key == "mock_key_for_dev":
            raise ConfigurationError(
                "GOOGLE_API_KEY environment variable is missing or invalid. "
                "Please set a valid key in .env or switch provider to 'mock' in configs/config.yaml."
            )
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        try:
            self._langchain_llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
                max_output_tokens=max_tokens,
                request_timeout=timeout,
            )
        except Exception as exc:
            raise ProviderError(
                f"Failed to initialize Google Gemini provider: {exc}"
            ) from exc

    def get_llm(self, framework: FrameworkType = FrameworkType.LANGCHAIN) -> Any:
        if framework == FrameworkType.LANGCHAIN:
            return self._langchain_llm
        elif framework == FrameworkType.SEMANTIC_KERNEL:
            try:
                import semantic_kernel as sk
                from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion

                kernel = sk.Kernel()
                kernel.add_service(
                    GoogleAIChatCompletion(
                        gemini_model_id=self.model_name,
                        api_key=self.api_key,
                    )
                )
                return kernel
            except ImportError:
                raise ConfigurationError(
                    "Semantic Kernel is not installed in the environment. Please install 'semantic-kernel' to use it."
                )
            except Exception as exc:
                raise ProviderError(
                    f"Failed to initialize Semantic Kernel Google provider: {exc}"
                ) from exc
        else:
            raise ConfigurationError(f"Unsupported framework type: '{framework}'")

    def create_tuned_model(self, dataset_path: str, display_name: str = "code-assistant-v1") -> str:
        """Read JSONL dataset and trigger fine-tuning job via Google GenAI Developer API using inline examples."""
        try:
            import json
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Read JSONL dataset into list of TuningExample objects
            tuning_examples: list[types.TuningExample] = []
            with open(dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    data = json.loads(line_str)
                    messages = data.get("messages", [])
                    user_text = ""
                    assistant_text = ""
                    for msg in messages:
                        if msg.get("role") == "user":
                            user_text = msg.get("content", "")
                        elif msg.get("role") == "assistant":
                            assistant_text = msg.get("content", "")
                    if user_text and assistant_text:
                        tuning_examples.append(
                            types.TuningExample(
                                text_input=user_text,
                                output=assistant_text,
                            )
                        )

            base_model_id = self.model_name
            if not base_model_id.startswith("models/") and not base_model_id.startswith("tunedModels/"):
                base_model_id = f"models/{base_model_id}"

            tuning_job = client.tunings.tune(
                base_model=base_model_id,
                training_dataset=types.TuningDataset(examples=tuning_examples),
                config=types.CreateTuningJobConfig(
                    tuned_model_display_name=display_name,
                    epoch_count=5,
                    batch_size=4,
                ),
            )

            tuned_model_id = getattr(tuning_job, "name", None) or f"tunedModels/{display_name}"
            return tuned_model_id
        except Exception as exc:
            raise ProviderError(f"Failed to trigger Google Fine-Tuning job via API: {exc}") from exc


    def check_tuned_model_ready(self, tuned_model_id: str) -> dict[str, Any]:
        """Query Google GenAI API to verify if the specified tuned model is active and ready."""
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            # Fetch model metadata from Google API
            model_info = client.models.get(model=tuned_model_id)
            state = getattr(model_info, "state", "SUCCEEDED")
            is_ready = str(state).upper() in ("SUCCEEDED", "ACTIVE", "READY", "JOB_STATE_SUCCEEDED")
            return {
                "ready": is_ready,
                "state": str(state),
                "model_id": tuned_model_id,
                "message": f"Model '{tuned_model_id}' status: {state}",
            }
        except Exception as exc:
            return {
                "ready": False,
                "state": "NOT_FOUND",
                "model_id": tuned_model_id,
                "message": f"Tuned model '{tuned_model_id}' is not available on Google API: {exc}",
            }



