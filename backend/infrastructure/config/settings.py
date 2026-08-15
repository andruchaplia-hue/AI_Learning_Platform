from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.domain.exceptions import ConfigurationError


class AppSettings(BaseSettings):
    """Application settings loaded from environment and config.yaml."""

    # Environment variables
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")

    # Yaml Config options (loaded dynamically from config.yaml)
    app_name: str = "ai-learning-platform"
    provider: str
    google_model: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
    min_length: int
    max_length: int

    # FAQ Configuration
    faq_top_k: int
    faq_similarity_threshold: float
    faq_high_confidence_threshold: float
    faq_json_path: str
    faq_vector_db_path: str
    faq_embedding_model: str
    faq_memory_db_path: str

    # Code Generation Configuration
    code_gen_tuned_model_id: str = ""
    code_gen_dataset_path: str
    code_gen_max_tokens: int

    # Image Captioning Configuration
    image_captioning_max_file_size_mb: int = 50
    image_captioning_allowed_formats: list[str] = Field(default_factory=lambda: ["png", "jpeg", "jpg", "webp", "gif"])
    image_captioning_upload_dir: str = "data/uploads"
    image_captioning_max_dimension: int = 2048

    # Auth Configuration
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    # Content Generation Configuration
    content_gen_max_prompt_length: int
    content_gen_top_k_examples: int
    content_gen_allowed_content_types: list[str]
    content_gen_planner_temperature: float
    content_gen_generator_temperature: float
    content_gen_vector_collection_prefix: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_settings(config_path: str | None = None) -> AppSettings:
    """Load configuration from config.yaml and environment variables.

    Raises:
        ConfigurationError: If config file is missing, invalid, or missing required keys.
    """
    yaml_config: dict[str, Any] = {}

    if config_path is None:
        root_dir = Path(__file__).resolve().parents[3]
        config_path = str(root_dir / "configs" / "config.yaml")

    path = Path(config_path)
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found at {config_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            if isinstance(content, dict):
                yaml_config = content
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to read or parse configuration file at {config_path}: {exc}"
        ) from exc

    try:
        app_cfg = yaml_config.get("application", {})
        llm_cfg = yaml_config["llm"]
        gen_cfg = yaml_config["generation"]
        val_cfg = yaml_config["validation"]
        google_cfg = llm_cfg["google"]
        faq_cfg = yaml_config["faq"]
        code_gen_cfg = yaml_config["code_generation"]
        img_cfg = yaml_config.get("image_captioning", {})
        auth_cfg = yaml_config["auth"]
        content_gen_cfg = yaml_config["content_generation"]

        kwargs: dict[str, Any] = {
            "app_name": app_cfg.get("name", "ai-learning-platform"),
            "provider": llm_cfg["provider"],
            "google_model": google_cfg["model"],
            "temperature": float(gen_cfg["temperature"]),
            "max_tokens": int(gen_cfg["max_tokens"]),
            "timeout_seconds": float(gen_cfg["timeout_seconds"]),
            "min_length": int(val_cfg["min_length"]),
            "max_length": int(val_cfg["max_length"]),
            "faq_top_k": int(faq_cfg["top_k"]),
            "faq_similarity_threshold": float(faq_cfg["similarity_threshold"]),
            "faq_high_confidence_threshold": float(faq_cfg["high_confidence_threshold"]),
            "faq_json_path": str(faq_cfg["faq_json_path"]),
            "faq_vector_db_path": str(faq_cfg["vector_db_path"]),
            "faq_embedding_model": str(faq_cfg["embedding_model"]),
            "faq_memory_db_path": str(faq_cfg["memory_db_path"]),
            "code_gen_tuned_model_id": str(code_gen_cfg.get("tuned_model_id", "")),
            "code_gen_dataset_path": str(code_gen_cfg["dataset_path"]),
            "code_gen_max_tokens": int(code_gen_cfg["max_code_tokens"]),
            "image_captioning_max_file_size_mb": int(img_cfg.get("max_file_size_mb", 50)),
            "image_captioning_allowed_formats": list(img_cfg.get("allowed_formats", ["png", "jpeg", "jpg", "webp", "gif"])),
            "image_captioning_upload_dir": str(img_cfg.get("upload_dir", "data/uploads")),
            "image_captioning_max_dimension": int(img_cfg.get("max_dimension", 2048)),
            "jwt_secret_key": str(auth_cfg["jwt_secret_key"]),
            "jwt_algorithm": str(auth_cfg["jwt_algorithm"]),
            "access_token_expire_minutes": int(auth_cfg["access_token_expire_minutes"]),
            "content_gen_max_prompt_length": int(content_gen_cfg["max_prompt_length"]),
            "content_gen_top_k_examples": int(content_gen_cfg["top_k_examples"]),
            "content_gen_allowed_content_types": list(content_gen_cfg["allowed_content_types"]),
            "content_gen_planner_temperature": float(content_gen_cfg["planner_temperature"]),
            "content_gen_generator_temperature": float(content_gen_cfg["generator_temperature"]),
            "content_gen_vector_collection_prefix": str(content_gen_cfg["vector_collection_prefix"]),
        }

        return AppSettings(**kwargs)
    except KeyError as key_err:
        raise ConfigurationError(
            f"Missing required configuration key in config.yaml: {key_err}"
        ) from key_err
    except Exception as exc:
        raise ConfigurationError(f"Failed to initialize AppSettings: {exc}") from exc


def get_settings() -> AppSettings:
    """FastAPI dependency wrapper for loading application settings."""
    return load_settings()

