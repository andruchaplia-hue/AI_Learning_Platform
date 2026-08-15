from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    """Centralized environment configuration controller for the frontend application."""

    host: str = Field(default="0.0.0.0", alias="HOST")
    backend_port: int = Field(default=8001, alias="BACKEND_PORT")
    frontend_port: int = Field(default=8501, alias="FRONTEND_PORT")
    backend_url_override: str | None = Field(default=None, alias="BACKEND_URL")
    app_env: str = "dev"

    @property
    def backend_url(self) -> str:
        """Dynamically construct backend URL or use container network override."""
        if self.backend_url_override:
            return self.backend_url_override.rstrip("/")
        return f"http://localhost:{self.backend_port}"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_frontend_settings() -> FrontendSettings:
    """Return cached singleton instance of FrontendSettings."""
    return FrontendSettings()
