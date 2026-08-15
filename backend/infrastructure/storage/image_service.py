import base64
import io
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from PIL import Image

from backend.domain.exceptions import InternalError, ValidationError

logger = logging.getLogger("backend.infrastructure.storage.image_service")


@dataclass
class ProcessedImage:
    processed_bytes: bytes
    resized: bool
    original_resolution: str
    processed_resolution: str
    mime_type: str
    base64_str: str


class ImageService:
    """Unified Backend Service for image validation, downscaling, compression, and isolated storage."""

    def __init__(self, base_upload_dir: str = "data/uploads") -> None:
        self.base_upload_dir = Path(base_upload_dir)
        try:
            self.base_upload_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error(f"Failed to create base upload directory {self.base_upload_dir}: {exc}")
            raise InternalError(f"Storage initialization error: {exc}") from exc

    def validate_image(
        self,
        content_bytes: bytes,
        filename: str = "image.png",
        max_file_size_mb: int = 10,
        allowed_formats: list[str] | None = None,
    ) -> str:
        """Validate raw image bytes (size, extension, PIL validity)."""
        if not content_bytes:
            raise ValidationError("Uploaded file is empty.")

        size_mb = len(content_bytes) / (1024 * 1024)
        if size_mb > max_file_size_mb:
            raise ValidationError(
                f"Image file size ({size_mb:.2f} MB) exceeds maximum allowed limit of {max_file_size_mb} MB."
            )

        ext = Path(filename).suffix.lstrip(".").lower() or "png"
        allowed = allowed_formats or ["png", "jpeg", "jpg", "webp", "gif"]
        if ext not in allowed:
            raise ValidationError(
                f"Unsupported image format '{ext}'. Allowed formats are: {', '.join(allowed)}."
            )

        try:
            with Image.open(io.BytesIO(content_bytes)) as img:
                img.verify()
        except Exception as exc:
            raise ValidationError(f"Invalid or corrupted image file: {exc}") from exc

        return ext

    def process_image(
        self,
        content_bytes: bytes,
        filename: str = "image.png",
        max_dimension: int = 1024,
    ) -> ProcessedImage:
        """Normalize color space, resize proportionally if exceeding max_dimension, and compress."""
        try:
            img = Image.open(io.BytesIO(content_bytes))
            orig_w, orig_h = img.size
            orig_res = f"{orig_w}x{orig_h}"

            img_format = (img.format or "JPEG").upper()
            if img_format not in ["JPEG", "PNG", "WEBP", "GIF"]:
                img_format = "JPEG"

            # Color space normalization
            if img.mode in ("RGBA", "LA", "P") and img_format in ("JPEG", "JPG"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                img = background
            elif img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            resized = False
            new_w, new_h = orig_w, orig_h

            if max(orig_w, orig_h) > max_dimension:
                scale = max_dimension / float(max(orig_w, orig_h))
                new_w = max(1, int(orig_w * scale))
                new_h = max(1, int(orig_h * scale))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                resized = True

            proc_res = f"{new_w}x{new_h}"

            output_buffer = io.BytesIO()
            save_format = "JPEG" if img_format == "JPG" else img_format
            img.save(output_buffer, format=save_format, quality=85)
            proc_bytes = output_buffer.getvalue()

            mime_type = f"image/{img_format.lower()}"
            if mime_type == "image/jpg":
                mime_type = "image/jpeg"

            b64_encoded = base64.b64encode(proc_bytes).decode("utf-8")

            return ProcessedImage(
                processed_bytes=proc_bytes,
                resized=resized,
                original_resolution=orig_res,
                processed_resolution=proc_res,
                mime_type=mime_type,
                base64_str=b64_encoded,
            )
        except Exception as exc:
            raise ValidationError(f"Failed to process or resize image: {exc}") from exc

    def save_image(
        self,
        content_bytes: bytes,
        original_filename: str = "image.png",
        user_id: str | None = None,
    ) -> str:
        """Save file bytes locally inside optional user subdirectory and return relative path string."""
        ext = Path(original_filename).suffix.lower() or ".png"
        filename = f"img_{uuid.uuid4().hex[:12]}{ext}"

        if user_id:
            target_dir = self.base_upload_dir / user_id
            rel_path = f"{user_id}/{filename}"
        else:
            target_dir = self.base_upload_dir
            rel_path = filename

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / filename
            target_path.write_bytes(content_bytes)
            logger.info(f"Saved image to {target_path} ({len(content_bytes)} bytes)")
            return rel_path
        except Exception as exc:
            logger.error(f"Failed to write image file to {target_dir}: {exc}")
            raise InternalError(f"Failed to save image to local storage: {exc}") from exc
