"""Auth service — authentication, user/group CRUD, permission resolution."""

from datetime import datetime, timedelta

import jwt
from loguru import logger
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import Group, User
from app.config import settings
from app.exceptions import AppError, DuplicateError, NotFoundError

# Permission actions available per module
PERMISSION_ACTIONS = ["view", "edit", "delete", "settings"]

# Modules that have permissions
PERMISSION_MODULES = ["collector", "creator", "briefing", "distributor", "crm"]


class AuthService:
    """Authentication, user management, and permission resolution."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Authentication ---

    async def login(
        self, tenant_id: str, email: str, password: str
    ) -> tuple[User, str]:
        """Authenticate user and return (user, jwt_token)."""
        result = await self.db.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.email == email,
                User.active.is_(True),
            )
        )
        user = result.scalar_one_or_none()
        if not user or not bcrypt.verify(password, user.password_hash):
            raise AppError("Ungueltige Zugangsdaten", 401)

        user.last_login_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(user)

        token = self._create_token(user)
        logger.info("User login: {email}", email=user.email)
        return user, token

    def _create_token(self, user: User) -> str:
        """Create a JWT token for a platform user."""
        payload = {
            "sub": str(user.id),
            "tenant_id": user.tenant_id,
            "email": user.email,
            "role": user.role,
            "type": "platform",
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiry_hours),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    async def get_user_from_token(self, token: str) -> User:
        """Validate JWT and return platform user."""
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as e:
            raise AppError("Token abgelaufen", 401) from e
        except jwt.InvalidTokenError as e:
            raise AppError("Ungueltiger Token", 401) from e

        if payload.get("type") != "platform":
            raise AppError("Ungueltiger Token-Typ", 401)

        user_id = int(payload["sub"])
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.groups))
            .where(User.id == user_id, User.active.is_(True))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise AppError("Benutzer nicht gefunden", 401)
        return user

    # --- User CRUD ---

    async def list_users(self, tenant_id: str) -> list[User]:
        """List all users for a tenant."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.groups))
            .where(User.tenant_id == tenant_id)
            .order_by(User.id)
        )
        return list(result.scalars().all())

    async def get_user(self, tenant_id: str, user_id: int) -> User:
        """Get a single user by ID."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.groups))
            .where(User.tenant_id == tenant_id, User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User", user_id)
        return user

    async def create_user(self, tenant_id: str, data: dict) -> User:
        """Create a new platform user."""
        existing = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id, User.email == data["email"])
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("User", "email")

        user = User(
            tenant_id=tenant_id,
            email=data["email"],
            password_hash=bcrypt.hash(data["password"]),
            display_name=data["display_name"],
            role=data.get("role", "user"),
            permissions=data.get("permissions"),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_user(self, tenant_id: str, user_id: int, data: dict) -> User:
        """Update user fields."""
        user = await self.get_user(tenant_id, user_id)

        if "email" in data and data["email"] != user.email:
            existing = await self.db.execute(
                select(User).where(
                    User.tenant_id == tenant_id, User.email == data["email"]
                )
            )
            if existing.scalar_one_or_none():
                raise DuplicateError("User", "email")

        for key, value in data.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete_user(self, tenant_id: str, user_id: int) -> None:
        """Deactivate a user (soft delete)."""
        user = await self.get_user(tenant_id, user_id)
        user.active = False
        await self.db.flush()

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        """Change own password after verifying current password."""
        if not bcrypt.verify(current_password, user.password_hash):
            raise AppError("Aktuelles Passwort ist falsch", 400)
        user.password_hash = bcrypt.hash(new_password)
        await self.db.flush()

    async def reset_password(
        self, tenant_id: str, user_id: int, new_password: str
    ) -> None:
        """Admin resets a user's password."""
        user = await self.get_user(tenant_id, user_id)
        user.password_hash = bcrypt.hash(new_password)
        await self.db.flush()

    # --- Group CRUD ---

    async def list_groups(self, tenant_id: str) -> list[Group]:
        """List all groups for a tenant."""
        result = await self.db.execute(
            select(Group)
            .options(selectinload(Group.users))
            .where(Group.tenant_id == tenant_id)
            .order_by(Group.id)
        )
        return list(result.scalars().all())

    async def get_group(self, tenant_id: str, group_id: int) -> Group:
        """Get a single group by ID."""
        result = await self.db.execute(
            select(Group)
            .options(selectinload(Group.users))
            .where(Group.tenant_id == tenant_id, Group.id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError("Group", group_id)
        return group

    async def create_group(self, tenant_id: str, data: dict) -> Group:
        """Create a new permission group."""
        existing = await self.db.execute(
            select(Group).where(
                Group.tenant_id == tenant_id, Group.name == data["name"]
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Group", "name")

        group = Group(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            permissions=data.get("permissions"),
        )
        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def update_group(self, tenant_id: str, group_id: int, data: dict) -> Group:
        """Update group fields."""
        group = await self.get_group(tenant_id, group_id)

        if "name" in data and data["name"] != group.name:
            existing = await self.db.execute(
                select(Group).where(
                    Group.tenant_id == tenant_id, Group.name == data["name"]
                )
            )
            if existing.scalar_one_or_none():
                raise DuplicateError("Group", "name")

        for key, value in data.items():
            if value is not None and hasattr(group, key):
                setattr(group, key, value)

        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def delete_group(self, tenant_id: str, group_id: int) -> None:
        """Delete a group."""
        group = await self.get_group(tenant_id, group_id)
        await self.db.delete(group)
        await self.db.flush()

    async def add_user_to_group(
        self, tenant_id: str, group_id: int, user_id: int
    ) -> None:
        """Add a user to a group."""
        group = await self.get_group(tenant_id, group_id)
        user = await self.get_user(tenant_id, user_id)
        if user not in group.users:
            group.users.append(user)
            await self.db.flush()

    async def remove_user_from_group(
        self, tenant_id: str, group_id: int, user_id: int
    ) -> None:
        """Remove a user from a group."""
        group = await self.get_group(tenant_id, group_id)
        user = await self.get_user(tenant_id, user_id)
        if user in group.users:
            group.users.remove(user)
            await self.db.flush()

    # --- Permission Resolution ---

    def resolve_permissions(self, user: User) -> dict:
        """Resolve effective permissions from user role, groups, and direct perms."""
        if user.role == "admin":
            return {
                mod: {action: True for action in PERMISSION_ACTIONS}
                for mod in PERMISSION_MODULES
            }

        result: dict[str, dict[str, bool]] = {
            mod: {action: False for action in PERMISSION_ACTIONS}
            for mod in PERMISSION_MODULES
        }

        # Merge group permissions (additive/union)
        for group in user.groups:
            if not group.permissions:
                continue
            for mod, actions in group.permissions.items():
                if mod in result:
                    for action, allowed in actions.items():
                        if action in result[mod] and allowed:
                            result[mod][action] = True

        # Merge direct user permissions (additive)
        if user.permissions:
            for mod, actions in user.permissions.items():
                if mod in result:
                    for action, allowed in actions.items():
                        if action in result[mod] and allowed:
                            result[mod][action] = True

        return result

    # --- Admin Seed ---

    async def ensure_admin_exists(self, tenant_id: str, password: str) -> User | None:
        """Create default admin if no users exist for tenant."""
        result = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id).limit(1)
        )
        if result.scalar_one_or_none():
            return None

        user = User(
            tenant_id=tenant_id,
            email="admin@go4.energy",
            password_hash=bcrypt.hash(password),
            display_name="Administrator",
            role="admin",
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        logger.info(
            "Admin user created: {email} (Tenant: {tenant})",
            email=user.email,
            tenant=tenant_id,
        )
        return user

    def get_permission_schema(self) -> dict:
        """Return available modules and their actions."""
        return {"modules": {mod: PERMISSION_ACTIONS for mod in PERMISSION_MODULES}}
