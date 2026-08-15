import re
import logging

logger = logging.getLogger("backend.service.autocomplete.utils")


def clean_option_prefix(text: str) -> str:
    """Remove leading bullets, numbers, and option tags like '1. ', '2. Option A:', '* '."""
    prefix_pattern = re.compile(
        r"^\s*(?:"
        r"\d+[\.\)]\s*(?:(?:Option|Choice)\s*[A-Za-z0-9]*:?|[A-Za-z]:\s*)?"
        r"|[\*\-\+]\s*(?:(?:Option|Choice)\s*[A-Za-z0-9]*:?|[A-Za-z]:\s*)?"
        r"|(?:Option|Choice)\s+[A-Za-z0-9]+:?"
        r")\s*",
        re.IGNORECASE,
    )
    cleaned = prefix_pattern.sub("", text).strip()
    return cleaned if cleaned else text.strip()


def split_options(text: str) -> list[str]:
    """Split the completion text into multiple options if it contains list markers."""
    text = text.strip()
    if not text:
        return []

    pattern = re.compile(
        r"(?:^|\n)"
        r"(\s*(?:"
        r"[\*\-\+]\s*(?:(?:Option|Choice)\s*[A-Za-z0-9]*:?|[A-Za-z]:\s*)?"
        r"|\d+[\.\)]\s*(?:(?:Option|Choice)\s*[A-Za-z0-9]*:?|[A-Za-z]:\s*)?"
        r"|(?:Option|Choice)\s+[A-Za-z0-9]+:?"
        r")\s*)",
        re.IGNORECASE,
    )

    matches = list(pattern.finditer(text))
    if not matches:
        return [clean_option_prefix(text)]

    if len(matches) == 1 and matches[0].start() == 0:
        return [clean_option_prefix(text)]

    options = []
    first_match_start = matches[0].start()
    pre_text = text[:first_match_start].strip()
    if pre_text:
        lower_pre = pre_text.lower()
        is_preamble = (
            lower_pre.endswith(":")
            or "option" in lower_pre
            or "completion" in lower_pre
            or "variant" in lower_pre
            or "choice" in lower_pre
            or "thought" in lower_pre
        )
        if not is_preamble:
            options.append(clean_option_prefix(pre_text))

    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        option_content = text[start:end].strip()
        cleaned_content = clean_option_prefix(option_content)
        if cleaned_content:
            options.append(cleaned_content)

    return options


def parse_provider_exception(exc: Exception) -> str:
    """Parse raw LLM provider exceptions into clean, user-friendly messages."""
    err_str = str(exc)
    err_type = type(exc).__name__.lower()

    if any(
        k in err_str.lower() or k in err_type
        for k in ["timeout", "timedout", "deadlineexceeded", "timed out"]
    ):
        return "The request to the AI service timed out. Please try again in a few moments."

    if any(
        k in err_str.lower() or k in err_type
        for k in [
            "429",
            "quota",
            "resourceexhausted",
            "rate_limit",
            "ratelimit",
            "quota exceeded",
            "rate limit",
            "rate_limit_exceeded",
        ]
    ):
        return (
            "The AI service quota or rate limit has been reached. "
            "Please try again later or select a model with available quota."
        )

    if any(
        k in err_str.lower() or k in err_type
        for k in [
            "401",
            "403",
            "unauthenticated",
            "invalid_api_key",
            "api_key_invalid",
            "permissiondenied",
        ]
    ):
        return "Authentication failed with the AI provider. Please verify your API key configuration."

    if any(
        k in err_str.lower() or k in err_type
        for k in ["404", "not_found", "model_not_found", "not found"]
    ):
        return "The selected AI model is currently unavailable or not found."

    return f"AI provider service error ({type(exc).__name__}). Please try again later."
