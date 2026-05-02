"""Email asset service — uploads, retrieval, deletion of tenant-scoped images.

Storage: ``backend/data/email_assets/{tenant_id}/{uuid}.{ext}``
Static URL: ``/api/static/email-assets/{tenant_id}/{filename}``

Security:
- Mime-type whitelist (images + PDF only)
- Max size enforced (default 5 MB)
- Filenames are UUID-prefixed to prevent path traversal / collisions
"""

from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.emailmarketing.models import EmailAsset
from app.exceptions import AppError

# Storage path under repo backend/. In Docker this should be a mounted volume.
DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "email_assets"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

# Public URL prefix (mounted in main.py as StaticFiles)
URL_PREFIX = "/api/static/email-assets"

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "application/pdf": ".pdf",
}

MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _slug(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]+", "-", name)
    return base.strip("-")[:80] or "asset"


def _tenant_dir(tenant_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", tenant_id)[:50]
    if not safe:
        raise AppError("Invalid tenant_id", 400)
    d = DATA_ROOT / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


class AssetService:
    """Email asset CRUD."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upload(
        self,
        tenant_id: str,
        *,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        content_stream,
        created_by: int | None = None,
    ) -> EmailAsset:
        if mime_type not in ALLOWED_MIME:
            raise AppError(
                f"Unzulässiger MIME-Typ: {mime_type}. Erlaubt: "
                + ", ".join(ALLOWED_MIME),
                400,
            )
        if size_bytes <= 0 or size_bytes > MAX_SIZE_BYTES:
            raise AppError(
                f"Datei-Größe {size_bytes} ist außerhalb des Bereichs 1..{MAX_SIZE_BYTES} Bytes",
                400,
            )

        ext = ALLOWED_MIME[mime_type]
        unique = uuid.uuid4().hex[:12]
        stem = _slug(Path(original_filename).stem)
        filename = f"{unique}_{stem}{ext}"

        dest_dir = _tenant_dir(tenant_id)
        dest_path = dest_dir / filename
        with dest_path.open("wb") as f:
            shutil.copyfileobj(content_stream, f)

        url_path = f"{URL_PREFIX}/{tenant_id}/{filename}"

        asset = EmailAsset(
            tenant_id=tenant_id,
            filename=filename,
            original_filename=original_filename[:300],
            mime_type=mime_type,
            size_bytes=size_bytes,
            url_path=url_path,
            created_by=created_by,
        )
        self.db.add(asset)
        await self.db.flush()
        await self.db.refresh(asset)
        logger.info(
            "Email asset hochgeladen: {file} ({size} B) für tenant {t}",
            file=original_filename,
            size=size_bytes,
            t=tenant_id,
        )
        return asset

    async def list_assets(self, tenant_id: str, limit: int = 200) -> list[EmailAsset]:
        result = await self.db.execute(
            select(EmailAsset)
            .where(EmailAsset.tenant_id == tenant_id)
            .order_by(EmailAsset.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, tenant_id: str, asset_id: int) -> EmailAsset | None:
        result = await self.db.execute(
            select(EmailAsset)
            .where(EmailAsset.id == asset_id)
            .where(EmailAsset.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, tenant_id: str, asset_id: int) -> bool:
        asset = await self.get_by_id(tenant_id, asset_id)
        if not asset:
            return False
        # Remove file from disk
        try:
            dest = _tenant_dir(tenant_id) / asset.filename
            if dest.exists():
                os.remove(dest)
        except Exception as e:
            logger.warning("Konnte Datei nicht entfernen: {e}", e=e)

        await self.db.delete(asset)
        await self.db.flush()
        return True
