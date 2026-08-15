import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_prompt(filename: str) -> str:
    """Load prompt template text from backend/use_cases/use_case_2/prompts/."""
    prompts_dir = Path(__file__).resolve().parent / "prompts"
    file_path = prompts_dir / filename
    if not file_path.exists():
        logger.error(f"Prompt template file not found: {file_path}")
        raise FileNotFoundError(f"Prompt template file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()
