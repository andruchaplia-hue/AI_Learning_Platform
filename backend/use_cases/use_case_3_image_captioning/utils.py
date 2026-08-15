import json
import logging
import re

logger = logging.getLogger(__name__)


def parse_caption_output(raw_text: str) -> tuple[str, str, str]:
    """Parse JSON or structured text response into short_caption, full_description, and action_description.

    Args:
        raw_text: Raw LLM output string from vision chain.

    Returns:
        Tuple of (short_caption, full_description, action_description).
    """
    clean_text = raw_text.strip()

    # Extract JSON code block if wrapped in markdown fences
    json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", clean_text, re.DOTALL)
    if json_match:
        clean_text = json_match.group(1)

    try:
        data = json.loads(clean_text)
        short = data.get("short_caption") or data.get("caption") or ""
        full = data.get("full_description") or data.get("description") or ""
        action = data.get("action_description") or data.get("actions") or "No distinct action detected."
        if short and full:
            return str(short).strip(), str(full).strip(), str(action).strip()
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.debug("Caption output is not valid JSON, falling back to plain text parsing.")

    # Fallback: plain text structured parsing
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    if not lines:
        return "Image description", clean_text, "No distinct action detected."

    short_caption = lines[0]
    full_description = "\n".join(lines[1:]) if len(lines) > 1 else clean_text
    action_description = "The image captures a static scene or moment."

    return short_caption, full_description, action_description
