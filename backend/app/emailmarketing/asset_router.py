"""Email asset endpoints — upload, list, delete."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.emailmarketing.asset_service import AssetService
from app.emailmarketing.schemas import EmailAssetResponse
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/emailmarketing/assets", tags=["emailmarketing"])


@router.get("", response_model=list[EmailAssetResponse])
async def list_assets(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[EmailAssetResponse]:
    service = AssetService(db)
    items = await service.list_assets(tenant_id)
    return [EmailAssetResponse.model_validate(a) for a in items]


@router.post(
    "",
    response_model=EmailAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailAssetResponse:
    """Upload a single image/file (max 5 MB, images + PDF only)."""
    try:
        # Read content into memory once to know size + buffer for write
        contents = await file.read()
        size = len(contents)
        if size <= 0:
            raise HTTPException(status_code=400, detail="Empty file")

        # Wrap bytes in a stream for the service
        from io import BytesIO

        stream = BytesIO(contents)
        service = AssetService(db)
        asset = await service.upload(
            tenant_id,
            original_filename=file.filename or "asset",
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=size,
            content_stream=stream,
        )
        await db.commit()
        return EmailAssetResponse.model_validate(asset)
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        await db.rollback()
        logger.exception("Asset upload failed")
        raise HTTPException(status_code=500, detail="Upload fehlgeschlagen") from e


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_asset(
    asset_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    service = AssetService(db)
    deleted = await service.delete(tenant_id, asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
