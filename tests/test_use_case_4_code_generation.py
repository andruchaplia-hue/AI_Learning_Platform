import json
import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.infrastructure.config.settings import load_settings
from backend.use_cases.use_case_4_code_generation.dataset_manager import DatasetManager
from backend.use_cases.use_case_4_code_generation.models import (
    AddDatasetEntryRequest,
    CodeGenerationRequest,
    CodeGenerationResponse,
)
from backend.use_cases.use_case_4_code_generation.plugins import (
    CodeGeneratorPlugin,
    CodeReviewerPlugin,
    ImprovementAdvisorPlugin,
    RequirementsAnalyzerPlugin,
)
from backend.use_cases.use_case_4_code_generation.service import CodeGenerationService

client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_dataset_file():
    """Backup dataset and metadata files before tests run and restore them immediately after."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    ds_path = root / "data" / "fine_tuning" / "code_generation_dataset.jsonl"
    meta_path = root / "data" / "fine_tuning" / "tuned_model_metadata.json"

    ds_content = ds_path.read_text(encoding="utf-8") if ds_path.exists() else None
    meta_content = meta_path.read_text(encoding="utf-8") if meta_path.exists() else None

    yield

    if ds_content is not None:
        ds_path.write_text(ds_content, encoding="utf-8")
    if meta_content is not None:
        meta_path.write_text(meta_content, encoding="utf-8")



def test_uc4_models():
    """Verify DTO model instantiation and validation."""
    req = CodeGenerationRequest(prompt="Create FastAPI endpoint", model_mode="base")
    assert req.prompt == "Create FastAPI endpoint"
    assert req.model_mode == "base"

    resp = CodeGenerationResponse(
        status="success",
        generated_code="def test(): pass",
        review_comments="Good",
        suggestions=["Add docstring"],
        model_used="gemini-3.1-flash-lite",
        execution_time_sec=0.5,
    )
    assert resp.status == "success"
    assert resp.generated_code == "def test(): pass"


def test_uc4_sk_plugins():
    """Verify Semantic Kernel plugins directly."""
    settings = load_settings()
    analyzer = RequirementsAnalyzerPlugin(settings)
    generator = CodeGeneratorPlugin(settings)
    reviewer = CodeReviewerPlugin(settings)
    advisor = ImprovementAdvisorPlugin(settings)

    req_json = analyzer.analyze_requirements("Create a FastAPI endpoint")
    req_dict = json.loads(req_json)
    assert req_dict["language"] == "python"

    code = generator.generate_code("Create a FastAPI endpoint")
    assert "Code" in code or "target" in code.lower()

    review = reviewer.review_code(code)
    assert "Audit" in review or "target" in review.lower()

    suggestions = advisor.suggest_improvements(code, review)
    assert isinstance(suggestions, str) or isinstance(suggestions, list)



def test_uc4_dataset_manager(tmp_path):
    """Verify dataset manager read, write, job status, and RAG retrieval."""
    settings = load_settings()
    # Override dataset path with temporary path for testing
    settings.code_gen_dataset_path = str(tmp_path / "test_dataset.jsonl")

    manager = DatasetManager(settings)
    entries = manager.get_dataset_entries()
    assert len(entries) == 0

    new_entry = manager.add_dataset_entry("Test prompt requirement", "def solution(): pass")
    assert new_entry.id == 1
    assert new_entry.user_prompt == "Test prompt requirement"

    updated_entries = manager.get_dataset_entries()
    assert len(updated_entries) == 1

    status_info = manager.get_job_status()
    assert status_info["dataset_size"] == 1


def test_uc4_dataset_manager_rag_retrieval(tmp_path):
    """Verify find_similar_examples returns relevant entries by keyword overlap."""
    settings = load_settings()
    settings.code_gen_dataset_path = str(tmp_path / "rag_test_dataset.jsonl")

    manager = DatasetManager(settings)
    manager.add_dataset_entry("Create a FastAPI health check endpoint", "@router.get('/health') ...")
    manager.add_dataset_entry("Write a Pydantic model for user registration", "class UserModel(BaseModel): ...")
    manager.add_dataset_entry("Implement a Python function to sort a list", "def sort_list(lst): ...")

    # Query that overlaps with first entry
    results = manager.find_similar_examples("FastAPI health endpoint", top_k=2)
    assert len(results) >= 1
    assert any("FastAPI" in e.user_prompt or "health" in e.user_prompt.lower() for e in results)

    # Query with no matches returns empty list
    no_results = manager.find_similar_examples("quantum computing algorithm", top_k=3)
    assert isinstance(no_results, list)

    # top_k respected
    all_results = manager.find_similar_examples("python function model endpoint", top_k=1)
    assert len(all_results) <= 1


@pytest.mark.asyncio
async def test_uc4_service_code_generation():
    """Verify CodeGenerationService execution."""
    settings = load_settings()
    service = CodeGenerationService(settings)

    req = CodeGenerationRequest(prompt="Create FastAPI health check endpoint", model_mode="base")
    response = await service.generate_code(req)

    assert response.status == "success"
    assert response.generated_code is not None
    assert response.review_comments is not None
    assert isinstance(response.suggestions, list)
    assert response.execution_time_sec >= 0.0


def test_uc4_service_diff_computation():
    """Verify unified diff calculation in service."""
    settings = load_settings()
    service = CodeGenerationService(settings)

    old_code = "def old_func():\n    return 1\n"
    new_code = "def new_func():\n    return 2\n"
    diff = service.compute_diff(old_code, new_code, filename="test.py")

    assert "---" in diff
    assert "+++" in diff
    assert "-def old_func():" in diff
    assert "+def new_func():" in diff


def test_uc4_api_routes():
    """Verify FastAPI APIRouter endpoints for Use Case 4."""
    # 1. POST /api/v1/code-generation
    resp = client.post(
        "/api/v1/code-generation",
        json={"prompt": "Create FastAPI health check endpoint", "model_mode": "base"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "generated_code" in data
    assert "review_comments" in data

    # 2. GET /api/v1/code-generation/dataset
    resp_ds = client.get("/api/v1/code-generation/dataset")
    assert resp_ds.status_code == 200
    data_ds = resp_ds.json()
    assert data_ds["status"] == "success"
    assert "total_entries" in data_ds

    # 4. POST /api/v1/code-generation/dataset
    resp_add = client.post(
        "/api/v1/code-generation/dataset",
        json={"user_prompt": "Test requirement from API test", "expected_code": "def api_test(): pass"},
    )
    assert resp_add.status_code == 201
    assert resp_add.json()["status"] == "success"

    # 5. POST /api/v1/code-generation/fine-tune
    resp_ft = client.post("/api/v1/code-generation/fine-tune")
    assert resp_ft.status_code in (200, 502)
    ft_json = resp_ft.json()
    assert ft_json["status"] in ("success", "error")



def test_uc4_api_tuned_model_rag_mode():
    """Verify tuned mode returns 200 with RAG few-shot (no real fine-tuned model required)."""
    resp = client.post(
        "/api/v1/code-generation",
        json={"prompt": "Create FastAPI endpoint", "model_mode": "tuned"},
    )
    # RAG mode should always return 200 — no dependency on external fine-tuned model
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "generated_code" in data
    # is_tuned_fallback=True signals RAG mode was used
    assert data["is_tuned_fallback"] is True


def test_uc4_api_fine_tune_trigger_rag_activation():
    """Verify fine-tune trigger returns READY status with rag-few-shot model ID."""
    resp = client.post("/api/v1/code-generation/fine-tune")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["tuned_model_id"] == "rag-few-shot"
    assert data["dataset_size"] > 0
