"""fetch_one — run adapter, persist snapshot, attach embedding."""

from __future__ import annotations

import hashlib
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.intel.adapters import AdapterError, get_adapter
from app.intel.models import IntelSnapshot, IntelSource
from app.intel.services.embedding_client import (
    EmbeddingUnavailableError,
    get_embedding_client,
)

_MAX_FAILURES_BEFORE_DEACTIVATE = 10


async def fetch_one(
    db: AsyncSession, source: IntelSource
) -> IntelSnapshot | None:
    """Fetch the source, persist a Snapshot, embed via TEI.

    Returns the new Snapshot on success, ``None`` if the fetch failed
    (in which case ``source.last_status='failed'`` is already set).
    """
    try:
        adapter = get_adapter(source.adapter)
        result = await adapter.fetch(source.config or {}, source.tenant_id)
    except AdapterError as e:
        source.last_status = "failed"
        source.last_error = str(e)[:1000]
        source.consecutive_failures = (source.consecutive_failures or 0) + 1
        source.last_fetched_at = datetime.utcnow()
        if source.consecutive_failures >= _MAX_FAILURES_BEFORE_DEACTIVATE:
            source.is_active = False
            logger.warning(
                "Intel source {sid} deactivated after {n} failures",
                sid=source.id,
                n=source.consecutive_failures,
            )
        await db.flush()
        return None
    except Exception as e:
        source.last_status = "failed"
        source.last_error = f"{type(e).__name__}: {e}"[:1000]
        source.consecutive_failures = (source.consecutive_failures or 0) + 1
        source.last_fetched_at = datetime.utcnow()
        logger.exception("Unexpected error fetching intel source {sid}", sid=source.id)
        await db.flush()
        return None

    text = result.text or ""
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    snap = IntelSnapshot(
        tenant_id=source.tenant_id,
        source_id=source.id,
        fetched_at=result.fetched_at,
        content_hash=content_hash,
        text=text,
        parsed=result.parsed or {},
        source_url=result.source_url[:2048] if result.source_url else None,
        byte_size=result.raw_size_bytes,
    )

    # Try embedding — failure is non-fatal, snapshot persists without it
    try:
        embedder = get_embedding_client()
        snap.embedding = await embedder.embed_one(text[:8000])  # bge-m3 max ~8k
    except EmbeddingUnavailableError as e:
        logger.info(
            "Embedding unavailable for source {sid} ({err}); snapshot saved without embedding",
            sid=source.id,
            err=str(e)[:200],
        )

    db.add(snap)
    source.last_status = "ok"
    source.last_error = None
    source.consecutive_failures = 0
    source.last_fetched_at = result.fetched_at
    await db.flush()
    await db.refresh(snap)
    logger.info(
        "Intel snapshot {sid} stored for source {srcid} ({bytes} bytes)",
        sid=snap.id,
        srcid=source.id,
        bytes=snap.byte_size or 0,
    )
    return snap
