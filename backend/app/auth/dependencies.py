"""Auth dependencies — JWT validation and permission checks for FastAPI."""

from fastapi import Depends, Request
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import AuthService
from app.config import settings
from app.database import get_db
from app.exceptions import AppError


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT token, return authenticated user."""
    auth_header = request.headers.get("Authorization", "")

    # Prefer Bearer token if present
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        service = AuthService(db)
        return await service.get_user_from_token(token)

    # Fallback: backend-secret for n8n and internal calls
    backend_secret = request.headers.get("X-Backend-Secret", "")
    if (
        backend_secret
        and settings.backend_secret
        and backend_secret == settings.backend_secret
    ):
        tenant_id = request.headers.get("X-Tenant-ID") or settings.active_tenant
        # Try to find a real admin user first
        stmt = (
            sa_select(User)
            .where(
                User.tenant_id == tenant_id,
                User.role == "admin",
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            return user
        # No admin in DB — create a transient admin object (not persisted)
        return User(
            id=0,
            tenant_id=tenant_id,
            email="system@internal",
            password_hash="",
            display_name="System",
            role="admin",
            active=True,
            groups=[],
        )

    raise AppError("Nicht authentifiziert", 401)


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an admin."""
    if user.role != "admin":
        raise AppError("Nur Administratoren haben Zugriff", 403)
    return user


def require_permission(module: str, action: str):
    """Factory: return a dependency that checks a specific permission."""

    async def _check(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if user.role == "admin":
            return user

        service = AuthService(db)
        perms = service.resolve_permissions(user)
        module_perms = perms.get(module, {})
        if not module_perms.get(action, False):
            raise AppError(f"Keine Berechtigung: {module}.{action}", 403)
        return user

    return _check
