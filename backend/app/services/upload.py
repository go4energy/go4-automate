"""Upload service for image files."""

import uuid
from pathlib import Path

from fastapi import UploadFile
from loguru import logger

from app.config import settings
from app.exceptions import ValidationError

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
EXTENSION_MAP = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class UploadService:
    """Service for handling file uploads."""

    async def save_image(self, tenant_id: str, file: UploadFile) -> str:
        """Validate and save an uploaded image. Returns the URL path."""
        if file.content_type not in ALLOWED_TYPES:
            raise ValidationError(
                f"Ungültiger Dateityp: {file.content_type}. "
                f"Erlaubt: JPEG, PNG, WebP"
            )

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        content = await file.read()
        if len(content) > max_bytes:
            raise ValidationError(
                f"Datei zu groß: max {settings.max_upload_size_mb} MB"
            )

        ext = EXTENSION_MAP[file.content_type]
        filename = f"{uuid.uuid4().hex}.{ext}"
        tenant_dir = Path(settings.upload_dir) / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        filepath = tenant_dir / filename
        filepath.write_bytes(content)

        url_path = f"/uploads/{tenant_id}/{filename}"
        logger.info(
            "Bild hochgeladen: {path} ({size} bytes)",
            path=url_path,
            size=len(content),
        )
        return url_path
