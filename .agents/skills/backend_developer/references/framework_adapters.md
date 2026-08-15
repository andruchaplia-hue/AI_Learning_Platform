# Framework Adapters Guidelines: Semantic Kernel & LangChain

This reference guide documents framework-specific patterns and attributes for Semantic Kernel and LangChain bindings within the platform.

---

## 1. Semantic Kernel (Python SDK)

### Prompt Execution Settings
- **Google GenAI / Gemini Provider**:
  - The model field for maximum tokens is `max_output_tokens`, NOT `max_tokens`.
  - Assigned execution settings inherit from Pydantic `PromptExecutionSettings` with `extra = 'forbid'`.
  - **Safe Pattern for Setting Assignment**:
    ```python
    req_settings = None
    try:
        req_settings = kernel.get_service().instantiate_prompt_execution_settings()
        try:
            req_settings.temperature = settings.temperature
        except Exception:
            pass
        try:
            if hasattr(req_settings, "max_output_tokens"):
                req_settings.max_output_tokens = settings.max_tokens
            elif hasattr(req_settings, "max_tokens"):
                req_settings.max_tokens = settings.max_tokens
        except Exception:
            pass
    except Exception:
        req_settings = None
    ```

### Function Registration
- **Mandatory Plugin Name**:
  - When calling `kernel.add_function()`, always provide `plugin_name` along with `function_name`:
    ```python
    sk_func = kernel.add_function(
        function_name="answer_faq",
        plugin_name="FAQPlugin",
        prompt=prompt_template
    )
    ```

---

## 2. Zero Fallbacks Policy

- **No Silent Error Swallowing**:
  - Never catch LLM or framework execution exceptions to return mock fallback text or raw dumps.
  - Fail fast by raising typed domain exceptions (`ProviderError`, `ValidationError`).
