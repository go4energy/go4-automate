"""Leadgen module API router - minimal Stage-1 skeleton.

Real endpoints (campaigns CRUD, runs, places) land in the next implementation
step. This file exists so the module registers cleanly and we can verify that
manifest discovery, model auto-import and Alembic migration all wire up.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/leadgen", tags=["leadgen"])


@router.get("/health")
async def health() -> dict:
    """Module health probe."""
    return {"module": "leadgen", "healthy": True}
