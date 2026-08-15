import logging
import uuid
from pathlib import Path

from backend.domain.exceptions import InternalError

logger = logging.getLogger("backend.infrastructure.storage")


class LocalStorageManager:
    """Manager for saving and retrieving files stored in local directory storage."""

    def __init__(self, upload_dir: str = "data/uploads") -> None:
        self.upload_dir = Path(upload_dir)
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error(f"Failed to create upload directory {self.upload_dir}: {exc}")
            raise InternalError(f"Storage initialization error: {exc}") from exc

    def save_file(self, content_bytes: bytes, original_filename: str = "image.png") -> str:
        """Save file bytes locally and return a generated unique image_id.

        Args:
            content_bytes: Raw bytes of the image file.
            original_filename: Original name of the uploaded file to preserve extension.

        Returns:
            Unique image_id (filename) stored in the upload directory.
        """
        ext = Path(original_filename).suffix.lower() or ".png"
        image_id = f"img_{uuid.uuid4().hex[:12]}{ext}"
        target_path = self.upload_dir / image_id

        try:
            target_path.write_bytes(content_bytes)
            logger.info(f"Saved uploaded image to {target_path} ({len(content_bytes)} bytes)")
            return image_id
        except Exception as exc:
            logger.error(f"Failed to write image file {target_path}: {exc}")
            raise InternalError(f"Failed to save image to local storage: {exc}") from exc

    def get_file_path(self, image_id: str) -> Path:
        """Retrieve absolute Path to saved file by image_id or relative path.

        Args:
            image_id: Unique filename identifier or user-scoped subpath (e.g. user_id/img_xxx.png).

        Returns:
            Path object pointing to the file.

        Raises:
            FileNotFoundError: If file does not exist in upload_dir.
        """
        clean_rel = image_id.lstrip("/\\")
        target_path = (self.upload_dir / clean_rel).resolve()

        # Security check: ensure path does not escape upload_dir
        if not str(target_path).startswith(str(self.upload_dir.resolve())):
            raise FileNotFoundError(f"Access to path '{image_id}' is outside upload storage.")

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Image '{image_id}' not found in storage.")
        return target_path
