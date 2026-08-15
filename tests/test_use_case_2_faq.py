import json
import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.infrastructure.config.settings import load_settings
from backend.infrastructure.memory.vectorstorage.chroma_store import ChromaStore
from backend.infrastructure.memory.vectorstorage.embedding_service import EmbeddingService

from backend.use_cases.use_case_2.models import FAQItem, RetrievedFAQ
from backend.use_cases.use_case_2.retriever import FAQRetriever
from backend.use_cases.use_case_2.plugins.faq_plugin import FAQPlugin
from backend.use_cases.use_case_2.plugins.analysis_plugins import QueryDecomposerPlugin, CoverageAnalyzerPlugin
from backend.use_cases.use_case_2.service import FAQService


@pytest.fixture
def test_settings():
    settings = load_settings()
    settings.provider = "mock"
    settings.faq_similarity_threshold = 0.1
    return settings


@pytest.fixture
def sample_faqs():
    return [
        FAQItem(id=1, category="Account", question="How do I reset my password?", answer="Click forgot password."),
        FAQItem(id=2, category="Billing", question="What payment methods are accepted?", answer="Visa, PayPal, Google Pay."),
    ]


@pytest.mark.asyncio
async def test_query_decomposer_plugin_simple(test_settings):
    decomposer = QueryDecomposerPlugin(test_settings)
    res_json = await decomposer.decompose_query("How do I reset my password?")
    res = json.loads(res_json)
    assert "questions" in res
    assert len(res["questions"]) == 1
    assert "reset my password?" in res["questions"][0]


@pytest.mark.asyncio
async def test_query_decomposer_plugin_compound(test_settings):
    decomposer = QueryDecomposerPlugin(test_settings)
    res_json = await decomposer.decompose_query("How do I reset my password and what payment methods are accepted?")
    res = json.loads(res_json)
    assert "questions" in res
    assert len(res["questions"]) >= 2


def _mock_embed(text: str) -> list[float]:
    import hashlib
    words = [w.lower().strip("?,.!\n\r:;()[]\"'") for w in text.split() if len(w) > 2]
    vec = [0.0] * 1536
    for w in words:
        idx = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % 1536
        vec[idx] += 1.0
    return vec


def test_chroma_store_search(test_settings, sample_faqs, monkeypatch):
    embedding_svc = EmbeddingService(test_settings)
    monkeypatch.setattr(embedding_svc, "embed_document", _mock_embed)
    monkeypatch.setattr(embedding_svc, "embed_query", _mock_embed)
    store = ChromaStore(test_settings, embedding_svc)
    store.index_faqs(sample_faqs)

    results = store.search("password reset", top_k=1)
    assert len(results) == 1
    assert results[0].id == 1
    assert results[0].score > 0.0


def test_faq_plugin_tool_calling(test_settings, sample_faqs, monkeypatch):
    embedding_svc = EmbeddingService(test_settings)
    monkeypatch.setattr(embedding_svc, "embed_document", _mock_embed)
    monkeypatch.setattr(embedding_svc, "embed_query", _mock_embed)
    store = ChromaStore(test_settings, embedding_svc)
    store.index_faqs(sample_faqs)

    retriever = FAQRetriever(store, embedding_svc)
    plugin = FAQPlugin(retriever, top_k=2, threshold=0.1)
    res_str = plugin.search_faq("How do I reset my password?")
    assert "status" in res_str
    assert "success" in res_str



@pytest.mark.asyncio
async def test_faq_service_process_query(test_settings, sample_faqs, monkeypatch):
    service = FAQService(test_settings)
    monkeypatch.setattr(service.embedding_service, "embed_document", _mock_embed)
    monkeypatch.setattr(service.embedding_service, "embed_query", _mock_embed)
    ret_faqs = [
        RetrievedFAQ(id=f.id, category=f.category, question=f.question, answer=f.answer, score=0.95)
        for f in sample_faqs
    ]

    async def _mock_agent_invoke(query, chat_history=None, **kwargs):
        metrics = {
            "decomposed_queries": [query],
            "max_similarity_score": 0.95,
            "coverage_score": 1.0,
            "missing_questions": [],
            "user_friendly": kwargs.get("user_friendly", True),
            "sk_filtering": kwargs.get("sk_filtering", True),
            "is_fallback": False,
        }
        return "Click forgot password.", ret_faqs, True, metrics

    monkeypatch.setattr(service.agent, "invoke", _mock_agent_invoke)

    from backend.use_cases.use_case_2.models import FAQQueryRequest

    req = FAQQueryRequest(query="How do I reset my password?", session_id="test_session_123")
    res = await service.process_query(req)

    assert res.status == "success"
    assert res.found is True
    assert len(res.answer) > 0
    assert res.execution_details is not None
    assert res.execution_details.max_similarity_score > 0.0

    # Test history retrieval
    history = service.get_session_history("test_session_123")
    assert len(history) >= 2


def test_faq_repository_save_and_auto_increment(test_settings):
    from backend.infrastructure.memory.storage.faq_repository import FAQRepository
    repo = FAQRepository(test_settings)
    
    new_item = FAQItem(id=0, category="Test", question="Test unique question?", answer="Test answer.")
    saved = repo.save_items([new_item])
    
    assert len(saved) == 1
    assert saved[0].id > 0
    assert saved[0].question == "Test unique question?"

    # Verify reloading from disk contains saved item
    all_items = repo.load_all()
    matching = [i for i in all_items if i.question == "Test unique question?"]
    assert len(matching) == 1
    assert matching[0].id == saved[0].id


def test_faq_fastapi_endpoints(monkeypatch):
    with TestClient(app) as client:
        service = client.app.state.faq_service

        async def _mock_agent_invoke(query, chat_history=None, **kwargs):
            metrics = {
                "decomposed_queries": [query],
                "max_similarity_score": 0.95,
                "coverage_score": 1.0,
                "missing_questions": [],
                "user_friendly": kwargs.get("user_friendly", True),
                "sk_filtering": kwargs.get("sk_filtering", True),
                "is_fallback": False,
            }
            return "Visa, PayPal, Google Pay.", [], True, metrics

        monkeypatch.setattr(service.agent, "invoke", _mock_agent_invoke)

        # Test Chat Endpoint
        chat_resp = client.post("/api/v1/faq/chat", json={"query": "What payment methods are supported?", "session_id": "api_test_session", "user_friendly": True, "sk_filtering": True})
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert data["status"] == "success"
        assert "answer" in data
        assert data["session_id"] == "api_test_session"

        # Test Reload Endpoint
        reload_resp = client.post("/api/v1/faq/reload")
        assert reload_resp.status_code == 200
        assert reload_resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_faq_service_user_friendly_false(test_settings, sample_faqs, monkeypatch):
    monkeypatch.setattr(EmbeddingService, "embed_document", lambda self, text: _mock_embed(text))
    monkeypatch.setattr(EmbeddingService, "embed_query", lambda self, text: _mock_embed(text))
    service = FAQService(test_settings)
    service.vector_store.index_faqs(sample_faqs)

    from backend.use_cases.use_case_2.models import FAQQueryRequest
    req = FAQQueryRequest(query="How do I reset my password?", session_id="test_session_456", user_friendly=False, sk_filtering=False)
    
    # We call actual agent invoke in mock mode (which triggers mock LLM skip)
    res = await service.process_query(req)
    assert res.status == "success"
    assert "Click forgot password." in res.answer


@pytest.mark.asyncio
async def test_faq_service_coverage_zero_fallback(test_settings, sample_faqs, monkeypatch):
    service = FAQService(test_settings)
    monkeypatch.setattr(service.embedding_service, "embed_document", _mock_embed)
    monkeypatch.setattr(service.embedding_service, "embed_query", _mock_embed)

    # Mock decomposer and coverage to return 0.0 coverage score
    async def _mock_agent_invoke(query, chat_history=None, **kwargs):
        metrics = {
            "decomposed_queries": [query],
            "max_similarity_score": 0.95,
            "coverage_score": 0.0,
            "missing_questions": [query],
            "user_friendly": kwargs.get("user_friendly", True),
            "sk_filtering": kwargs.get("sk_filtering", True),
            "selected_faq_ids": [],
            "is_fallback": True,
        }
        return "Unfortunately, no suitable answer was found in our knowledge base for your question. Please contact customer support at support@platform.com.", [], False, metrics

    monkeypatch.setattr(service.agent, "invoke", _mock_agent_invoke)

    from backend.use_cases.use_case_2.models import FAQQueryRequest
    req = FAQQueryRequest(query="how to make pizza", session_id="test_session_789")
    res = await service.process_query(req)
    
    assert res.found is False
    assert "support@platform.com" in res.answer


@pytest.mark.asyncio
async def test_faq_service_fallback_metrics(test_settings, sample_faqs, monkeypatch):
    service = FAQService(test_settings)
    monkeypatch.setattr(service.embedding_service, "embed_document", _mock_embed)
    monkeypatch.setattr(service.embedding_service, "embed_query", _mock_embed)

    ret_faqs = [
        RetrievedFAQ(id=f.id, category=f.category, question=f.question, answer=f.answer, score=0.95)
        for f in sample_faqs
    ]

    async def _mock_agent_invoke(query, chat_history=None, **kwargs):
        metrics = {
            "decomposed_queries": [query],
            "max_similarity_score": 0.95,
            "coverage_score": 1.0,
            "missing_questions": [],
            "user_friendly": True,
            "sk_filtering": True,
            "selected_faq_ids": [],
            "decomposer_fallback": True,
            "coverage_fallback": True,
            "pipeline_error": "LLM Connection Refused",
            "is_fallback": False,
        }
        return "Click forgot password.", ret_faqs, True, metrics

    monkeypatch.setattr(service.agent, "invoke", _mock_agent_invoke)

    from backend.use_cases.use_case_2.models import FAQQueryRequest
    req = FAQQueryRequest(query="How do I reset my password?", session_id="test_session_fallback")
    res = await service.process_query(req)

    assert res.status == "success"
    assert res.execution_details is not None
    assert res.execution_details.decomposer_fallback is True
    assert res.execution_details.coverage_fallback is True
    assert res.execution_details.pipeline_error == "LLM Connection Refused"


@pytest.mark.asyncio
async def test_faq_agent_live_google_gemini_integration(sample_faqs, monkeypatch):
    # Load actual production settings (reads from configs/config.yaml and .env)
    settings = load_settings()
    settings.provider = "google"
    settings.faq_similarity_threshold = 0.3

    # Define actual production-like FAQ candidates
    live_sample_faqs = [
        FAQItem(id=1950, category="General", question="What camera do I need?", answer="Any HD webcam or IP camera is suitable for using the application."),
        FAQItem(id=1952, category="Connection", question="What types of cameras are supported?", answer="The platform works with any IP cameras that support RTSP or ONVIF."),
        FAQItem(id=1953, category="Connection", question="Is it mandatory to buy an NVR?", answer="No, cameras can stream video directly to our cloud."),
    ]

    embedding_svc = EmbeddingService(settings)
    store = ChromaStore(settings, embedding_svc)
    store.index_faqs(live_sample_faqs)

    retriever = FAQRetriever(store, embedding_svc)
    plugin = FAQPlugin(retriever, top_k=3, threshold=0.3)

    from backend.use_cases.use_case_2.agent import FAQAgent
    agent = FAQAgent(settings, plugin)

    # Perform real call to Google Gemini
    answer, retrieved, is_found, metrics = await agent.invoke(
        query="which web camera should I choose for the application?",
        chat_history=[],
        user_friendly=True,
        sk_filtering=True
    )

    # Asserts to check if live Gemini calls worked without fallbacks
    assert metrics["decomposer_fallback"] is False, f"Decomposer failed: {metrics.get('pipeline_error')}"
    assert metrics["coverage_fallback"] is False, f"Coverage failed: {metrics.get('pipeline_error')}"
    assert is_found is True
    
    # Verify SK Agent Candidate Selection:
    # Under strict prompt settings, only the single most relevant FAQ (web camera FAQ #1950) must be selected.
    # Unrelated NVR (1953) and less specific generic IP-camera FAQ (1952) must be filtered out.
    assert metrics["selected_faq_ids"] == [1950], f"Expected selected_faq_ids to be strictly [1950], got {metrics['selected_faq_ids']}"





