import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api.app import app
from backend.domain.exceptions import ValidationError
from backend.infrastructure.config.settings import load_settings
from backend.use_cases.use_case_3_image_captioning.image_processor import process_image
from backend.use_cases.use_case_3_image_captioning.models import ImageCaptionResponse
from backend.use_cases.use_case_3_image_captioning.service import ImageCaptionService
from backend.use_cases.use_case_3_image_captioning.validators import validate_image_file


def create_dummy_image_bytes(width: int = 100, height: int = 100, format_name: str = "PNG") -> bytes:
    """Helper to generate dummy image bytes for testing."""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


def test_validate_image_file_valid():
    img_bytes = create_dummy_image_bytes(100, 100, "PNG")
    ext = validate_image_file(img_bytes, filename="test.png", max_file_size_mb=10)
    assert ext == "png"


def test_validate_image_file_empty():
    with pytest.raises(ValidationError, match="Uploaded file is empty"):
        validate_image_file(b"", filename="empty.png")


def test_validate_image_file_unsupported_format():
    img_bytes = create_dummy_image_bytes(50, 50, "PNG")
    with pytest.raises(ValidationError, match="Unsupported image format"):
        validate_image_file(img_bytes, filename="test.bmp", allowed_formats=["png", "jpg"])


def test_validate_image_file_corrupt():
    corrupt_bytes = b"not_an_image_data_stream_12345"
    with pytest.raises(ValidationError, match="Invalid or corrupted image"):
        validate_image_file(corrupt_bytes, filename="corrupt.png")


def test_process_image_resizing():
    # Large image exceeding 2048 limit
    large_img_bytes = create_dummy_image_bytes(3000, 1500, "JPEG")
    res = process_image(large_img_bytes, filename="large.jpg", max_dimension=2048)

    assert res.resized is True
    assert res.original_resolution == "3000x1500"
    assert res.processed_resolution == "2048x1024"
    assert res.base64_str is not None


@pytest.mark.asyncio
async def test_use_case_3_service_mock_provider(tmp_path):
    settings = load_settings()
    settings.provider = "mock"
    settings.image_captioning_upload_dir = str(tmp_path)

    service = ImageCaptionService(settings)
    img_bytes = create_dummy_image_bytes(200, 200, "PNG")

    response = await service.generate_caption(img_bytes, filename="test_sample.png")

    assert isinstance(response, ImageCaptionResponse)
    assert response.short_caption != ""
    assert response.full_description != ""
    assert response.action_description != ""
    assert response.execution_time_sec >= 0.0
    assert response.image_id.endswith(".png")


def test_image_caption_api_endpoints(tmp_path):
    settings = load_settings()
    settings.provider = "mock"
    settings.image_captioning_upload_dir = str(tmp_path)

    # Pre-populate app.state with a mock-configured service (matches singleton route pattern)
    app.state.image_caption_service = ImageCaptionService(settings)

    client = TestClient(app)
    img_bytes = create_dummy_image_bytes(150, 150, "JPEG")

    files = {"file": ("test_upload.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/image-caption", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "short_caption" in data
    assert "full_description" in data
    assert "action_description" in data
    assert "image_id" in data

    image_id = data["image_id"]
    get_res = client.get(f"/api/v1/image-caption/image/{image_id}")
    assert get_res.status_code == 200
    assert get_res.headers["content-type"] in ["image/jpeg", "image/png", "application/octet-stream"]
