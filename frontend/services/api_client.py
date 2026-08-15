import logging
from typing import Any
import httpx

from frontend.services.env_controller import get_frontend_settings

logger = logging.getLogger("frontend.services.api_client")


class APIClient:
    """Centralized HTTP client for communicating with FastAPI platform backend."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_frontend_settings()
        self.base_url = (base_url or settings.backend_url).rstrip("/")

    def _safe_json(self, resp: httpx.Response) -> Any:
        """Safely parse JSON response body for success and error status codes alike."""
        try:
            return resp.json()
        except Exception:
            return {"message": resp.text or f"HTTP Error {resp.status_code}"}

    def _send_request(
        self,
        method: str,
        path: str,
        *,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        json: Any = None,
        files: Any = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Centralized safe HTTP request sender with graceful network error handling."""
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    files=files,
                    params=params,
                )
                return {
                    "status_code": resp.status_code,
                    "data": self._safe_json(resp),
                    "raw_response": resp,
                }
        except httpx.ConnectError as exc:
            logger.error(f"Backend connection refused for {method} {url}: {exc}")
            return {
                "status_code": 503,
                "data": {"message": "Could not connect to backend server. Please ensure the backend service is running."},
                "raw_response": None,
                "error": "ConnectionRefused",
            }
        except httpx.TimeoutException as exc:
            logger.error(f"Backend request timed out for {method} {url}: {exc}")
            return {
                "status_code": 504,
                "data": {"message": "Request to backend timed out. Please try again."},
                "raw_response": None,
                "error": "Timeout",
            }
        except Exception as exc:
            logger.error(f"HTTP request error for {method} {url}: {exc}", exc_info=True)
            return {
                "status_code": 500,
                "data": {"message": f"Unexpected network or client error: {exc}"},
                "raw_response": None,
                "error": str(exc),
            }

    def get_health(self) -> dict[str, Any]:
        """Fetch health check status from backend."""
        res = self._send_request("GET", "/health", timeout=3.0)
        if res["status_code"] == 200 and isinstance(res["data"], dict):
            return res["data"]
        raise ConnectionError(res.get("data", {}).get("message", "Backend unavailable"))

    def get_version(self) -> dict[str, Any]:
        """Fetch version and active provider metadata from backend."""
        res = self._send_request("GET", "/version", timeout=3.0)
        if res["status_code"] == 200 and isinstance(res["data"], dict):
            return res["data"]
        raise ConnectionError(res.get("data", {}).get("message", "Backend unavailable"))

    def post_autocomplete(self, text: str, mode: str = "sentence") -> dict[str, Any]:
        """Post autocomplete generation request to UC1 endpoint."""
        return self._send_request(
            "POST",
            "/api/v1/autocomplete",
            json={"text": text, "mode": mode},
            timeout=45.0,
        )

    def post_faq_chat(
        self, query: str, session_id: str = "default_session", user_friendly: bool = True, sk_filtering: bool = True
    ) -> dict[str, Any]:
        """Post FAQ chatbot query to UC2 endpoint."""
        return self._send_request(
            "POST",
            "/api/v1/faq/chat",
            json={
                "query": query,
                "session_id": session_id,
                "user_friendly": user_friendly,
                "sk_filtering": sk_filtering,
            },
            timeout=45.0,
        )

    def reload_faq_index(self) -> dict[str, Any]:
        """Post reload request to re-index FAQ dataset."""
        res = self._send_request("POST", "/api/v1/faq/reload", timeout=30.0)
        return {"status_code": res["status_code"], "data": res["data"] if res["status_code"] == 200 else None}

    def post_faq_item(self, item_id: int, category: str, question: str, answer: str) -> dict[str, Any]:
        """Post new FAQ item to add to knowledge base."""
        res = self._send_request(
            "POST",
            "/api/v1/faq/item",
            json={"id": item_id, "category": category, "question": question, "answer": answer},
            timeout=30.0,
        )
        return {"status_code": res["status_code"], "data": res["data"] if res["status_code"] in (200, 201) else None}

    def post_faq_bulk(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Post bulk JSON items list to add to knowledge base."""
        res = self._send_request(
            "POST",
            "/api/v1/faq/bulk",
            json=items,
            timeout=45.0,
        )
        return {"status_code": res["status_code"], "data": res["data"] if res["status_code"] in (200, 201) else None}

    def post_faq_parse_text(self, raw_text: str) -> dict[str, Any]:
        """Post unstructured text string to parse into FAQ items and index."""
        res = self._send_request(
            "POST",
            "/api/v1/faq/parse-text",
            json={"raw_text": raw_text},
            timeout=45.0,
        )
        return {"status_code": res["status_code"], "data": res["data"] if res["status_code"] in (200, 201) else None}

    def post_code_generation(
        self,
        prompt: str,
        model_mode: str = "base",
        target_filename: str | None = None,
        target_file_content: str | None = None,
        session_id: str = "default_session",
    ) -> dict[str, Any]:
        """Post code generation request to UC4 endpoint."""
        return self._send_request(
            "POST",
            "/api/v1/code-generation",
            json={
                "prompt": prompt,
                "model_mode": model_mode,
                "target_filename": target_filename,
                "target_file_content": target_file_content,
                "session_id": session_id,
            },
            timeout=60.0,
        )

    def post_code_diff(
        self,
        prompt: str,
        target_filename: str,
        target_file_content: str,
        model_mode: str = "base",
    ) -> dict[str, Any]:
        """Post refactoring request to UC4 diff endpoint."""
        return self._send_request(
            "POST",
            "/api/v1/code-generation/diff",
            json={
                "prompt": prompt,
                "model_mode": model_mode,
                "target_filename": target_filename,
                "target_file_content": target_file_content,
            },
            timeout=60.0,
        )

    def get_code_gen_dataset(self) -> dict[str, Any]:
        """Fetch fine-tuning JSONL dataset entries."""
        return self._send_request("GET", "/api/v1/code-generation/dataset", timeout=15.0)

    def post_code_gen_dataset(self, user_prompt: str, expected_code: str) -> dict[str, Any]:
        """Add new example pair to fine-tuning dataset."""
        return self._send_request(
            "POST",
            "/api/v1/code-generation/dataset",
            json={"user_prompt": user_prompt, "expected_code": expected_code},
            timeout=15.0,
        )

    def trigger_fine_tune_job(self) -> dict[str, Any]:
        """Fetch fine-tuning job status and dataset readiness metrics."""
        return self._send_request("POST", "/api/v1/code-generation/fine-tune", timeout=15.0)

    def post_image_caption(
        self, file_bytes: bytes, filename: str = "image.png", mime_type: str = "image/png"
    ) -> dict[str, Any]:
        """Post multipart image file upload for UC3 caption generation."""
        files = {"file": (filename, file_bytes, mime_type)}
        return self._send_request(
            "POST",
            "/api/v1/image-caption",
            files=files,
            timeout=60.0,
        )

    def get_stored_image_url(self, image_id: str) -> str:
        """Construct public backend URL to retrieve saved image file."""
        return f"{self.base_url}/api/v1/image-caption/image/{image_id}"

    # -------------------------------------------------------------------------
    # Use Case 5: Auth, Profile & Content Generator Endpoints
    # -------------------------------------------------------------------------

    def _auth_headers(self, token: str | None) -> dict[str, str]:
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def register(self, username: str, email: str, password: str) -> dict[str, Any]:
        """Register a new user account."""
        return self._send_request(
            "POST",
            "/api/v1/auth/register",
            json={"username": username, "email": email, "password": password},
            timeout=15.0,
        )

    def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate user and obtain JWT token."""
        return self._send_request(
            "POST",
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=15.0,
        )

    def get_dev_users(self) -> dict[str, Any]:
        """Fetch list of registered users for quick dev login."""
        return self._send_request("GET", "/api/v1/auth/dev-users", timeout=10.0)

    def dev_login(self, identifier: str) -> dict[str, Any]:
        """Perform fast dev authentication by email or username."""
        return self._send_request(
            "POST",
            "/api/v1/auth/dev-login",
            json={"identifier": identifier},
            timeout=15.0,
        )

    def get_me(self, token: str) -> dict[str, Any]:
        """Fetch current authenticated user info."""
        return self._send_request(
            "GET",
            "/api/v1/auth/me",
            headers=self._auth_headers(token),
            timeout=10.0,
        )

    def get_profile(self, token: str) -> dict[str, Any]:
        """Fetch user profile."""
        return self._send_request(
            "GET",
            "/api/v1/profile",
            headers=self._auth_headers(token),
            timeout=10.0,
        )

    def update_profile(self, profile_data: dict[str, Any], token: str) -> dict[str, Any]:
        """Update user profile."""
        return self._send_request(
            "PUT",
            "/api/v1/profile",
            headers=self._auth_headers(token),
            json=profile_data,
            timeout=15.0,
        )

    def post_content_generation(
        self,
        content_type: str,
        prompt: str,
        token: str,
        image_base64: str | None = None,
        image_mime_type: str | None = None,
        use_personalization_dataset: bool = True,
    ) -> dict[str, Any]:
        """Generate personalized content using UC5 agent pipeline."""
        payload = {
            "content_type": content_type,
            "prompt": prompt,
            "image_base64": image_base64,
            "image_mime_type": image_mime_type,
            "use_personalization_dataset": use_personalization_dataset,
        }
        return self._send_request(
            "POST",
            "/api/v1/content-generation",
            headers=self._auth_headers(token),
            json=payload,
            timeout=90.0,
        )

    def get_content_history(self, token: str) -> dict[str, Any]:
        """Fetch user content generation history."""
        return self._send_request(
            "GET",
            "/api/v1/content-generation/history",
            headers=self._auth_headers(token),
            timeout=15.0,
        )

    def submit_content_post(
        self,
        prompt: str,
        content_type: str,
        generated_content: str,
        plan_breakdown: str = "",
        image_path: str = "",
        rating: int = 5,
        save_to_dataset: bool = False,
        token: str = "",
    ) -> dict[str, Any]:
        """Submit and publish finalized post to the author's wall."""
        return self._send_request(
            "POST",
            "/api/v1/content-generation/submit",
            headers=self._auth_headers(token),
            json={
                "prompt": prompt,
                "content_type": content_type,
                "generated_content": generated_content,
                "plan_breakdown": plan_breakdown,
                "image_path": image_path,
                "rating": rating,
                "save_to_dataset": save_to_dataset,
            },
            timeout=15.0,
        )

    def post_content_feedback(
        self, history_id: str, rating: int, save_to_dataset: bool, token: str
    ) -> dict[str, Any]:
        """Submit feedback rating for generated content."""
        return self._send_request(
            "POST",
            "/api/v1/content-generation/feedback",
            headers=self._auth_headers(token),
            json={"history_id": history_id, "rating": rating, "save_to_dataset": save_to_dataset},
            timeout=15.0,
        )

    def get_image_url(self, image_path: str) -> str:
        """Return absolute backend URL for serving stored image."""
        clean_path = str(image_path).lstrip("/")
        return f"{self.base_url}/api/v1/image-caption/image/{clean_path}"

    def _normalize_image_path(self, image_path: str) -> str:
        """Extract clean relative image path from full URL or raw path."""
        path = str(image_path).strip()
        if "/api/v1/image-caption/image/" in path:
            path = path.split("/api/v1/image-caption/image/")[-1]
        elif path.startswith("http://") or path.startswith("https://"):
            parts = path.split("/", 3)
            if len(parts) > 3:
                path = parts[3]
        return path.lstrip("/")

    def get_image_bytes(self, image_path: str) -> bytes | None:
        """Fetch stored image binary bytes from backend via HTTP for rendering directly in Streamlit."""
        if not image_path:
            return None
        clean_path = self._normalize_image_path(image_path)
        url = f"{self.base_url}/api/v1/image-caption/image/{clean_path}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return resp.content
                logger.warning(f"Failed to fetch image bytes ({resp.status_code}): {url}")
        except Exception as exc:
            logger.error(f"Error fetching image bytes from backend: {exc}")

        return None

    def get_writing_samples(self, token: str) -> dict[str, Any]:
        """Fetch user personal writing samples."""
        return self._send_request(
            "GET",
            "/api/v1/content-generation/examples",
            headers=self._auth_headers(token),
            timeout=15.0,
        )

    def post_writing_sample(
        self, title: str, content_type: str, content: str, tags: list[str], token: str
    ) -> dict[str, Any]:
        """Add new writing sample to personal dataset."""
        return self._send_request(
            "POST",
            "/api/v1/content-generation/examples",
            headers=self._auth_headers(token),
            json={"title": title, "content_type": content_type, "content": content, "tags": tags},
            timeout=15.0,
        )

    def delete_writing_sample(self, sample_id: str, token: str) -> dict[str, Any]:
        """Delete writing sample."""
        return self._send_request(
            "DELETE",
            f"/api/v1/content-generation/examples/{sample_id}",
            headers=self._auth_headers(token),
            timeout=15.0,
        )

    def export_dataset_url(self) -> str:
        """Return endpoint URL for downloading JSONL dataset."""
        return f"{self.base_url}/api/v1/content-generation/examples/export/jsonl"
