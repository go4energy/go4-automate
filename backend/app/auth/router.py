"""Auth router — login, user/group CRUD, permission management."""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.auth.schemas import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    LoginRequest,
    PasswordChange,
    PasswordReset,
    TokenResponse,
    UserCreate,
    UserMeResponse,
    UserResponse,
    UserUpdate,
)
from app.auth.service import AuthService
from app.database import get_db
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Public ---


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email and password."""
    try:
        service = AuthService(db)
        user, token = await service.login(tenant_id, data.email, data.password)
        user_resp = UserResponse.model_validate(user)
        return TokenResponse(access_token=token, user=user_resp)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in login")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Authenticated ---


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMeResponse:
    """Get current user with resolved permissions."""
    try:
        service = AuthService(db)
        perms = service.resolve_permissions(user)
        groups = [
            GroupResponse(
                id=g.id,
                tenant_id=g.tenant_id,
                name=g.name,
                description=g.description,
                permissions=g.permissions,
                user_count=len(g.users) if hasattr(g, "users") and g.users else 0,
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
            for g in user.groups
        ]
        return UserMeResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            resolved_permissions=perms,
            groups=groups,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_me")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/me/password")
async def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change own password."""
    try:
        service = AuthService(db)
        await service.change_password(user, data.current_password, data.new_password)
        return {"detail": "Passwort geaendert"}
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in change_password")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Admin: Users ---


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all users (admin only)."""
    try:
        service = AuthService(db)
        return await service.list_users(tenant_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_users")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: UserCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user (admin only)."""
    try:
        service = AuthService(db)
        return await service.create_user(tenant_id, data.model_dump())
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_user")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get a single user (admin only)."""
    try:
        service = AuthService(db)
        return await service.get_user(tenant_id, user_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_user")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user (admin only)."""
    try:
        service = AuthService(db)
        update_data = data.model_dump(exclude_unset=True)
        return await service.update_user(tenant_id, user_id, update_data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_user")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a user (admin only)."""
    try:
        service = AuthService(db)
        await service.delete_user(tenant_id, user_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_user")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    data: PasswordReset,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reset a user's password (admin only)."""
    try:
        service = AuthService(db)
        await service.reset_password(tenant_id, user_id, data.new_password)
        return {"detail": "Passwort zurueckgesetzt"}
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in reset_password")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Admin: Groups ---


@router.get("/groups", response_model=list[GroupResponse])
async def list_groups(
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[GroupResponse]:
    """List all groups (admin only)."""
    try:
        service = AuthService(db)
        groups = await service.list_groups(tenant_id)
        return [
            GroupResponse(
                id=g.id,
                tenant_id=g.tenant_id,
                name=g.name,
                description=g.description,
                permissions=g.permissions,
                user_count=len(g.users) if g.users else 0,
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
            for g in groups
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_groups")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/groups",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    data: GroupCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    """Create a permission group (admin only)."""
    try:
        service = AuthService(db)
        group = await service.create_group(tenant_id, data.model_dump())
        return GroupResponse(
            id=group.id,
            tenant_id=group.tenant_id,
            name=group.name,
            description=group.description,
            permissions=group.permissions,
            user_count=0,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    data: GroupUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    """Update a group (admin only)."""
    try:
        service = AuthService(db)
        update_data = data.model_dump(exclude_unset=True)
        group = await service.update_group(tenant_id, group_id, update_data)
        return GroupResponse(
            id=group.id,
            tenant_id=group.tenant_id,
            name=group.name,
            description=group.description,
            permissions=group.permissions,
            user_count=len(group.users) if group.users else 0,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a group (admin only)."""
    try:
        service = AuthService(db)
        await service.delete_group(tenant_id, group_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/groups/{group_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_user_to_group(
    group_id: int,
    user_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Add a user to a group (admin only)."""
    try:
        service = AuthService(db)
        await service.add_user_to_group(tenant_id, group_id, user_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in add_user_to_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete(
    "/groups/{group_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_user_from_group(
    group_id: int,
    user_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a user from a group (admin only)."""
    try:
        service = AuthService(db)
        await service.remove_user_from_group(tenant_id, group_id, user_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in remove_user_from_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Permission Schema ---


@router.get("/permissions/schema")
async def get_permission_schema(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return available modules and actions for permission matrix."""
    service = AuthService(db)
    return service.get_permission_schema()
