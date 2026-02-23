"""Auth schemas — request/response models for authentication and user management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Login credentials."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response after successful login."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserCreate(BaseModel):
    """Create a new user (admin action)."""

    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)
    display_name: str = Field(..., max_length=200)
    role: str = Field("user", pattern=r"^(admin|user)$")
    permissions: dict | None = None


class UserUpdate(BaseModel):
    """Update user fields (admin action)."""

    email: str | None = Field(None, max_length=255)
    display_name: str | None = Field(None, max_length=200)
    role: str | None = Field(None, pattern=r"^(admin|user)$")
    active: bool | None = None
    permissions: dict | None = None


class UserResponse(BaseModel):
    """User data returned from API."""

    id: int
    tenant_id: str
    email: str
    display_name: str
    role: str
    active: bool
    last_login_at: datetime | None = None
    permissions: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(BaseModel):
    """Current user with resolved permissions."""

    id: int
    email: str
    display_name: str
    role: str
    resolved_permissions: dict
    groups: list["GroupResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class PasswordChange(BaseModel):
    """Change own password."""

    current_password: str
    new_password: str = Field(..., min_length=6)


class PasswordReset(BaseModel):
    """Admin resets user password."""

    new_password: str = Field(..., min_length=6)


class GroupCreate(BaseModel):
    """Create a permission group."""

    name: str = Field(..., max_length=100)
    description: str | None = None
    permissions: dict | None = None


class GroupUpdate(BaseModel):
    """Update a permission group."""

    name: str | None = Field(None, max_length=100)
    description: str | None = None
    permissions: dict | None = None


class GroupResponse(BaseModel):
    """Group data returned from API."""

    id: int
    tenant_id: str
    name: str
    description: str | None = None
    permissions: dict | None = None
    user_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionSchema(BaseModel):
    """Available permission actions per module."""

    modules: dict[str, list[str]]
