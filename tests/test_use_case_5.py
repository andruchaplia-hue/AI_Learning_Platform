import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api.app import app
from backend.domain.exceptions import AuthenticationError, ValidationError
from backend.infrastructure.auth.jwt_manager import JWTManager
from backend.infrastructure.auth.password_hasher import PasswordHasher
from backend.infrastructure.auth.user_repository import UserRepository
from backend.infrastructure.config.settings import load_settings
from backend.use_cases.use_case_5_content_gen.dataset_service import PersonalizationDatasetService
from backend.use_cases.use_case_5_content_gen.models import (
    ContentFeedbackRequest,
    ContentGenerationRequest,
    ContentSubmitRequest,
    UserProfileUpdateRequest,
    UserRegisterRequest,
    UserLoginRequest,
    WritingSampleCreateRequest,
)
from backend.use_cases.use_case_5_content_gen.auth_service import AuthService
from backend.use_cases.use_case_5_content_gen.profile_service import ProfileService
from backend.use_cases.use_case_5_content_gen.service import ContentGenerationService


# -----------------------------------------------------------------------------
# 1. Password Hasher Tests
# -----------------------------------------------------------------------------

def test_password_hasher():
    raw_pwd = "SuperSecretPassword123"
    hashed = PasswordHasher.hash_password(raw_pwd)

    assert hashed != raw_pwd
    assert PasswordHasher.verify_password(raw_pwd, hashed) is True
    assert PasswordHasher.verify_password("WrongPassword", hashed) is False
    assert PasswordHasher.verify_password("", hashed) is False

    with pytest.raises(ValueError):
        PasswordHasher.hash_password("")


# -----------------------------------------------------------------------------
# 2. JWT Manager Tests
# -----------------------------------------------------------------------------

def test_jwt_manager():
    settings = load_settings()
    jwt_mgr = JWTManager(settings)

    payload_data = {"sub": "user-123", "username": "alice", "email": "alice@example.com"}
    token = jwt_mgr.create_access_token(payload_data)

    assert isinstance(token, str)
    decoded = jwt_mgr.decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["username"] == "alice"

    with pytest.raises(AuthenticationError):
        jwt_mgr.decode_token("")

    with pytest.raises(AuthenticationError):
        jwt_mgr.decode_token("invalid.jwt.token")


# -----------------------------------------------------------------------------
# 3. User Repository Tests
# -----------------------------------------------------------------------------

def test_user_repository(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = UserRepository(db_path=str(db_file))

    # Create user
    hashed_pwd = PasswordHasher.hash_password("password123")
    user = repo.create_user(username="bob", email="bob@example.com", password_hash=hashed_pwd)

    assert user["username"] == "bob"
    assert user["email"] == "bob@example.com"
    assert "id" in user

    # Duplicate user should raise ValidationError
    with pytest.raises(ValidationError):
        repo.create_user(username="bob", email="bob2@example.com", password_hash=hashed_pwd)

    with pytest.raises(ValidationError):
        repo.create_user(username="bob2", email="bob@example.com", password_hash=hashed_pwd)

    # Fetch user
    by_email = repo.get_user_by_email("bob@example.com")
    assert by_email is not None
    assert by_email["id"] == user["id"]

    by_id = repo.get_user_by_id(user["id"])
    assert by_id is not None
    assert by_id["username"] == "bob"

    # Profile CRUD
    profile = repo.get_user_profile(user["id"])
    assert profile is not None
    assert profile["username"] == "bob"

    updated_prof = repo.update_user_profile(
        user["id"],
        {
            "profession": "Architect",
            "industry": "Cloud",
            "age": 32,
            "gender": "Male",
            "hobbies": ["Kubernetes", "AI"],
            "bio": "Use diagrams and clear structure.",
        },
    )
    assert updated_prof["profession"] == "Architect"
    assert "Kubernetes" in updated_prof["hobbies"]
    assert updated_prof["age"] == 32
    assert updated_prof["gender"] == "Male"

    # Content history
    history = repo.save_content_history(
        user_id=user["id"],
        content_type="blog_post",
        prompt="Write about Docker",
        generated_content="# Docker Guide",
        plan_breakdown="Step 1: Introduction",
    )
    assert history["content_type"] == "blog_post"

    hist_list = repo.get_content_history(user["id"])
    assert len(hist_list) == 1
    assert hist_list[0]["id"] == history["id"]

    feedback_res = repo.update_content_feedback(
        history_id=history["id"], user_id=user["id"], rating=5, save_to_dataset=True
    )
    assert feedback_res["rating"] == 5
    assert feedback_res["saved_to_dataset"] is True

    # Writing samples
    sample = repo.save_writing_sample(
        user_id=user["id"],
        title="Microservices Primer",
        content_type="blog_post",
        content="Microservices decouple systems...",
        tags=["architecture"],
    )
    assert sample["title"] == "Microservices Primer"

    samples = repo.list_writing_samples(user["id"])
    assert len(samples) == 1
    assert samples[0]["id"] == sample["id"]

    deleted = repo.delete_writing_sample(sample["id"], user["id"])
    assert deleted is True
    assert len(repo.list_writing_samples(user["id"])) == 0


# -----------------------------------------------------------------------------
# 4. Personalization Dataset Service Tests
# -----------------------------------------------------------------------------

def test_personalization_dataset_service(tmp_path):
    settings = load_settings()
    settings.provider = "mock"
    settings.faq_vector_db_path = str(tmp_path / "chroma")
    db_file = tmp_path / "memory.db"

    repo = UserRepository(db_path=str(db_file))
    user = repo.create_user("charlie", "charlie@example.com", PasswordHasher.hash_password("secret"))

    ds_service = PersonalizationDatasetService(settings, repo)

    sample = ds_service.add_writing_sample(
        user_id=user["id"],
        title="Clean Architecture in Python",
        content_type="blog_post",
        content="Clean Architecture separates business logic from infrastructure.",
        tags=["python", "clean-architecture"],
    )
    assert sample["id"] is not None

    samples_list = ds_service.list_writing_samples(user["id"])
    assert len(samples_list) == 1

    similar = ds_service.find_similar_samples(user["id"], query_text="Python Architecture", top_k=2)
    assert len(similar) >= 1

    jsonl = ds_service.export_dataset_jsonl(user["id"])
    assert "Clean Architecture" in jsonl

    ds_service.delete_writing_sample(sample["id"], user["id"])
    assert len(ds_service.list_writing_samples(user["id"])) == 0


# -----------------------------------------------------------------------------
# 5. Content Generation Service (Mock Mode) Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_content_generation_service(tmp_path):
    settings = load_settings()
    settings.provider = "mock"
    settings.faq_vector_db_path = str(tmp_path / "chroma")
    settings.faq_memory_db_path = str(tmp_path / "memory.db")

    auth_service = AuthService(settings)
    profile_service = ProfileService(settings)
    content_service = ContentGenerationService(settings)

    # 1. Register
    reg_resp = await auth_service.register_user(
        UserRegisterRequest(username="david", email="david@example.com", password="password123")
    )
    assert reg_resp.username == "david"
    assert reg_resp.access_token is not None

    # 2. Login
    login_resp = await auth_service.login_user(
        UserLoginRequest(email="david@example.com", password="password123")
    )
    assert login_resp.access_token is not None

    # 3. Get / Update profile
    prof = await profile_service.get_profile(reg_resp.user_id)
    assert prof.username == "david"

    updated_prof = await profile_service.update_profile(
        reg_resp.user_id,
        UserProfileUpdateRequest(
            profession="Lead AI Architect",
            age=34,
            gender="Male",
            hobbies=["Generative AI", "Bouldering"],
            bio="Lead AI Architect with 12+ years designing distributed systems.",
        ),
    )
    assert updated_prof.profession == "Lead AI Architect"
    assert updated_prof.age == 34
    assert updated_prof.gender == "Male"

    # 4. Generate content (creates draft in response, does not write to history yet)
    gen_resp = await content_service.generate_content(
        user_id=reg_resp.user_id,
        req=ContentGenerationRequest(
            content_type="social_media_post",
            prompt="Ugh, back to work already and it's only day one. 47 merge requests waiting.",
            use_personalization_dataset=True,
        ),
    )
    assert gen_resp.content_type == "social_media_post"
    assert gen_resp.generated_content != ""
    assert gen_resp.plan_breakdown != ""
    assert len(gen_resp.decision_chain) == 5
    assert gen_resp.execution_time >= 0.0

    # Unsubmitted draft is NOT in history yet
    history_pre = await content_service.get_history(reg_resp.user_id)
    assert len(history_pre) == 0

    # 5. Submit finalized post to publish to Author Wall
    submitted_post = await content_service.submit_post(
        user_id=reg_resp.user_id,
        req=ContentSubmitRequest(
            prompt=gen_resp.prompt,
            content_type=gen_resp.content_type,
            generated_content=gen_resp.generated_content,
            plan_breakdown=gen_resp.plan_breakdown,
            rating=5,
            save_to_dataset=True,
        ),
    )
    assert submitted_post.rating == 5
    assert submitted_post.saved_to_dataset is True

    # 6. Now history contains exactly the submitted post
    history = await content_service.get_history(reg_resp.user_id)
    assert len(history) == 1
    assert history[0].id == submitted_post.id

    # Second feedback submission on the same history item should be idempotent
    fb_result2 = await content_service.submit_feedback(
        user_id=reg_resp.user_id,
        req=ContentFeedbackRequest(history_id=submitted_post.id, rating=5, save_to_dataset=True),
    )
    assert fb_result2["rating"] == 5

    samples = content_service.dataset_service.list_writing_samples(reg_resp.user_id)
    assert len(samples) == 1

    # Verify decision chain enrichment
    assert "👤 Profile" in gen_resp.decision_chain[0]["stage"]
    assert "🧠 Few-Shot Personalization Retrieval" in gen_resp.decision_chain[1]["stage"]
    assert "🖼️ Multimodal Vision Extraction" in gen_resp.decision_chain[2]["stage"]
    assert "📋 Editorial Strategy & Outlining" in gen_resp.decision_chain[3]["stage"]
    assert "Synthesized editorial strategy" in gen_resp.decision_chain[3]["details"]
    assert "✨ Tone Calibration & Generation" in gen_resp.decision_chain[4]["stage"]
    assert "words" in gen_resp.decision_chain[4]["details"]


def test_agent_vision_sanitization(tmp_path):
    settings = load_settings()
    settings.provider = "mock"
    from backend.use_cases.use_case_5_content_gen.agent import ContentAgentPipeline

    pipeline = ContentAgentPipeline(settings)

    # 1. Test string with trailing signature
    raw_str = (
        "Visual observation of modern office space.\n"
        "{'extras': {'signature': 'EnEKbwERTTIPsvxy3bYt/LKNoI6c+MsZycUJN3UlQYOs9zvgUqho0ysNH/xXfcKQKNHP6hP'}}"
    )
    clean_str = pipeline._sanitize_extracted_text(raw_str)
    assert "Visual observation of modern office space." in clean_str
    assert "extras" not in clean_str
    assert "signature" not in clean_str

    # 2. Test list of dicts output from multimodal Gemini
    raw_list = [
        {"type": "text", "text": "A laptop on a wooden desk."},
        {"type": "thought", "text": "internal thought"},
        {"extras": {"signature": "abc123xyz"}},
    ]
    clean_list = pipeline._sanitize_extracted_text(raw_list)
    assert "A laptop on a wooden desk." in clean_list
    assert "signature" not in clean_list


@pytest.mark.asyncio
async def test_content_generation_with_image_persistence(tmp_path):
    settings = load_settings()
    settings.provider = "mock"
    settings.faq_vector_db_path = str(tmp_path / "chroma")
    settings.faq_memory_db_path = str(tmp_path / "memory.db")
    settings.image_captioning_upload_dir = str(tmp_path / "uploads")

    from PIL import Image
    import io

    # Generate dummy image
    img = Image.new("RGB", (1200, 800), color=(0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")

    auth_service = AuthService(settings)
    content_service = ContentGenerationService(settings)

    reg = await auth_service.register_user(
        UserRegisterRequest(username="photographer", email="photo@example.com", password="password123")
    )

    gen_resp = await content_service.generate_content(
        user_id=reg.user_id,
        req=ContentGenerationRequest(
            content_type="blog_post",
            prompt="Write a review of our high performance cloud servers.",
            image_base64=b64_data,
            image_mime_type="image/jpeg",
        ),
    )

    assert gen_resp.visual_context_used is True
    assert "Extracted visual features & narrative cues:" in gen_resp.decision_chain[2]["details"]
    assert gen_resp.image_path != ""
    assert reg.user_id in gen_resp.image_path

    # Verify physically stored on disk
    saved_file = Path(settings.image_captioning_upload_dir) / gen_resp.image_path
    assert saved_file.exists()

    # Draft is not in history until submitted
    hist_pre = await content_service.get_history(reg.user_id)
    assert len(hist_pre) == 0

    # Submit post
    submitted = await content_service.submit_post(
        user_id=reg.user_id,
        req=ContentSubmitRequest(
            prompt=gen_resp.prompt,
            content_type=gen_resp.content_type,
            generated_content=gen_resp.generated_content,
            image_path=gen_resp.image_path,
            rating=5,
        ),
    )
    assert submitted.image_path == gen_resp.image_path

    history = await content_service.get_history(reg.user_id)
    assert len(history) == 1
    assert history[0].image_path == gen_resp.image_path
# -----------------------------------------------------------------------------
# 6. API Route Integration Tests (FastAPI TestClient)
# -----------------------------------------------------------------------------

def test_use_case_5_api_endpoints(tmp_path):
    settings = load_settings()
    settings.provider = "mock"
    settings.faq_vector_db_path = str(tmp_path / "chroma")
    settings.faq_memory_db_path = str(tmp_path / "api_memory.db")

    from backend.infrastructure.config.settings import get_settings
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        client = TestClient(app)

        # 1. Unauthenticated call to protected endpoint must return 401
        unauth_resp = client.get("/api/v1/profile")
        assert unauth_resp.status_code == 401
        assert unauth_resp.json()["status"] == "error"

        # 2. Register
        reg_res = client.post(
            "/api/v1/auth/register",
            json={"username": "tester_dev", "email": "tester@example.com", "password": "securepassword123"},
        )
        assert reg_res.status_code == 200
        auth_data = reg_res.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2.1 Fast Dev Auth (dev-users list & dev-login)
        dev_users_res = client.get("/api/v1/auth/dev-users")
        assert dev_users_res.status_code == 200
        dev_users = dev_users_res.json()
        assert len(dev_users) >= 1
        assert any(u["username"] == "tester_dev" for u in dev_users)

        dev_login_res = client.post("/api/v1/auth/dev-login", json={"identifier": "tester@example.com"})
        assert dev_login_res.status_code == 200
        assert dev_login_res.json()["username"] == "tester_dev"
        assert "access_token" in dev_login_res.json()

        # 3. Get /me
        me_res = client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "tester_dev"

        # 4. Profile GET & PUT
        prof_res = client.get("/api/v1/profile", headers=headers)
        assert prof_res.status_code == 200

        put_prof = client.put(
            "/api/v1/profile",
            headers=headers,
            json={
                "profession": "Senior ML Engineer",
                "age": 29,
                "gender": "Female",
                "hobbies": ["LLMs"],
                "bio": "Passionate ML engineer",
            },
        )
        assert put_prof.status_code == 200
        assert put_prof.json()["profession"] == "Senior ML Engineer"
        assert put_prof.json()["age"] == 29
        assert put_prof.json()["gender"] == "Female"

        # 5. Writing Samples (Dataset) CRUD
        add_sample = client.post(
            "/api/v1/content-generation/examples",
            headers=headers,
            json={
                "title": "Intro to LCEL",
                "content_type": "blog_post",
                "content": "LangChain Expression Language provides declarative composition.",
                "tags": ["langchain"],
            },
        )
        assert add_sample.status_code == 200
        sample_id = add_sample.json()["id"]

        list_samples = client.get("/api/v1/content-generation/examples", headers=headers)
        assert list_samples.status_code == 200
        assert list_samples.json()["total_count"] == 1

        # 6. Generate Content (draft in memory)
        gen_res = client.post(
            "/api/v1/content-generation",
            headers=headers,
            json={
                "content_type": "linkedin_post",
                "prompt": "Announcing our new AI Learning Platform release with LangChain.",
                "use_personalization_dataset": True,
            },
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert "generated_content" in gen_data
        assert "plan_breakdown" in gen_data
        assert gen_data["content_type"] == "linkedin_post"

        # Prior to submission, history is empty
        hist_pre = client.get("/api/v1/content-generation/history", headers=headers)
        assert hist_pre.status_code == 200
        assert len(hist_pre.json()) == 0

        # 7. Submit post to publish to Author Wall
        submit_res = client.post(
            "/api/v1/content-generation/submit",
            headers=headers,
            json={
                "content_type": gen_data["content_type"],
                "prompt": gen_data["prompt"],
                "generated_content": gen_data["generated_content"],
                "plan_breakdown": gen_data["plan_breakdown"],
                "rating": 5,
                "save_to_dataset": True,
            },
        )
        assert submit_res.status_code == 200
        assert submit_res.json()["rating"] == 5

        # 8. History now contains submitted post
        hist_res = client.get("/api/v1/content-generation/history", headers=headers)
        assert hist_res.status_code == 200
        assert len(hist_res.json()) == 1

        fb_res = client.post(
            "/api/v1/content-generation/feedback",
            headers=headers,
            json={"history_id": submit_res.json()["id"], "rating": 5, "save_to_dataset": True},
        )
        assert fb_res.status_code == 200

        # 8. Export JSONL dataset
        export_res = client.get("/api/v1/content-generation/examples/export/jsonl", headers=headers)
        assert export_res.status_code == 200
        assert "messages" in export_res.text

        # 9. Delete sample
        del_res = client.delete(f"/api/v1/content-generation/examples/{sample_id}", headers=headers)
        assert del_res.status_code == 200
    finally:
        app.dependency_overrides.clear()
