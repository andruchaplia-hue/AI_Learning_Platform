import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes.auth import router as auth_router
from backend.api.routes.autocomplete import router as autocomplete_router
from backend.api.routes.code_generation import router as code_generation_router
from backend.api.routes.content_examples import router as content_examples_router
from backend.api.routes.content_generation import router as content_generation_router
from backend.api.routes.faq import router as faq_router
from backend.api.routes.image_caption import router as image_caption_router
from backend.api.routes.profile import router as profile_router
from backend.domain.exceptions import (
    AuthenticationError,
    ConfigurationError,
    InternalError,
    ProviderError,
    ValidationError,
)
from backend.infrastructure.config.settings import AppSettings, get_settings
from backend.use_cases.use_case_1_autocomplete.service import AutocompleteService
from backend.use_cases.use_case_2.service import FAQService
from backend.use_cases.use_case_3_image_captioning.service import ImageCaptionService

# Configure logging
logging_config_path = Path(__file__).resolve().parents[2] / "configs" / "logging.yaml"
if logging_config_path.exists():
    with open(logging_config_path, "r", encoding="utf-8") as f:
        log_cfg = yaml.safe_load(f)
        logging.config.dictConfig(log_cfg)

logger = logging.getLogger("backend.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize singleton services on startup."""
    settings = get_settings()
    logger.info("Lifespan startup: initializing singleton services...")
    app.state.autocomplete_service = AutocompleteService(settings)
    app.state.faq_service = FAQService(settings)
    app.state.image_caption_service = ImageCaptionService(settings)
    logger.info("Services initialized and stored in app.state.")
    yield
    logger.info("Lifespan shutdown: cleaning up resources.")


app = FastAPI(
    title="AI Learning Platform API",
    description="FastAPI backend serving unified AI Learning Platform use cases (LangChain & Semantic Kernel)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware setup for Streamlit frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health & System Status Endpoints
@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version", tags=["System"])
async def get_version(settings: AppSettings = Depends(get_settings)) -> dict[str, str]:
    return {
        "version": "1.0.0",
        "app_name": settings.app_name,
        "provider": settings.provider,
    }


# Global Exception Handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    logger.warning(f"ValidationError on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": "error", "message": exc.message},
    )


@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    logger.warning(f"AuthenticationError on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"status": "error", "message": exc.message},
    )


@app.exception_handler(ConfigurationError)
async def configuration_exception_handler(
    request: Request, exc: ConfigurationError
) -> JSONResponse:
    logger.error(f"ConfigurationError on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": exc.message},
    )


@app.exception_handler(ProviderError)
async def provider_exception_handler(
    request: Request, exc: ProviderError
) -> JSONResponse:
    logger.error(f"ProviderError on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"status": "error", "message": exc.message},
    )


@app.exception_handler(InternalError)
async def internal_exception_handler(
    request: Request, exc: InternalError
) -> JSONResponse:
    logger.error(f"InternalError on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": exc.message},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled Exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected internal server error occurred. Please try again later.",
        },
    )


# Register all Use Case and Auth routes
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(autocomplete_router)
app.include_router(faq_router)
app.include_router(image_caption_router)
app.include_router(code_generation_router)
app.include_router(content_generation_router)
app.include_router(content_examples_router)
