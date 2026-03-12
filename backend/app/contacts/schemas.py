"""Contacts schemas - Pydantic models for API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============== Company Schemas ==============


class CompanyBase(BaseModel):
    """Base schema for Company."""

    name: str = Field(..., min_length=1, max_length=200)
    domain: str | None = Field(None, max_length=200)
    website: str | None = Field(None, max_length=500)
    logo_url: str | None = Field(None, max_length=500)
    industry: str | None = Field(None, max_length=100)
    size: str | None = Field(None, max_length=50)
    annual_revenue: str | None = Field(None, max_length=50)
    address: dict | None = None
    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    description: str | None = None


class CompanyCreate(CompanyBase):
    """Schema for creating a Company."""

    owner_id: int | None = None


class CompanyUpdate(BaseModel):
    """Schema for updating a Company."""

    name: str | None = Field(None, min_length=1, max_length=200)
    domain: str | None = Field(None, max_length=200)
    website: str | None = Field(None, max_length=500)
    logo_url: str | None = Field(None, max_length=500)
    industry: str | None = Field(None, max_length=100)
    size: str | None = Field(None, max_length=50)
    annual_revenue: str | None = Field(None, max_length=50)
    address: dict | None = None
    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    description: str | None = None
    owner_id: int | None = None


class CompanyResponse(CompanyBase):
    """Schema for Company response."""

    id: int
    tenant_id: str
    owner_id: int | None
    created_at: datetime
    updated_at: datetime
    contact_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CompanyListResponse(BaseModel):
    """Schema for Company list response."""

    id: int
    tenant_id: str
    name: str
    domain: str | None
    website: str | None
    logo_url: str | None
    industry: str | None
    size: str | None
    tags: list[str]
    contact_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Contact Schemas ==============


class ContactBase(BaseModel):
    """Base schema for Contact."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=200)
    phone: str | None = Field(None, max_length=50)
    mobile: str | None = Field(None, max_length=50)
    position: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)
    source: str | None = Field(None, max_length=100)
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    linkedin: str | None = Field(None, max_length=200)
    twitter: str | None = Field(None, max_length=200)
    notes: str | None = None


class ContactCreate(ContactBase):
    """Schema for creating a Contact."""

    company_id: int | None = None
    owner_id: int | None = None


class ContactUpdate(BaseModel):
    """Schema for updating a Contact."""

    email: EmailStr | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    phone: str | None = Field(None, max_length=50)
    mobile: str | None = Field(None, max_length=50)
    position: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)
    source: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    custom_fields: dict | None = None
    linkedin: str | None = Field(None, max_length=200)
    twitter: str | None = Field(None, max_length=200)
    notes: str | None = None
    company_id: int | None = None
    owner_id: int | None = None


class ContactResponse(ContactBase):
    """Schema for Contact response."""

    id: int
    tenant_id: str
    company_id: int | None
    owner_id: int | None
    created_at: datetime
    updated_at: datetime
    company_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ContactListResponse(BaseModel):
    """Schema for Contact list response."""

    id: int
    tenant_id: str
    email: str
    name: str
    phone: str | None
    position: str | None
    avatar_url: str | None
    source: str | None
    tags: list[str]
    company_id: int | None
    company_name: str | None = None
    owner_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Bulk Operation Schemas ==============


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete request."""

    ids: list[int] = Field(..., min_length=1)


class BulkTagRequest(BaseModel):
    """Schema for bulk tag request."""

    ids: list[int] = Field(..., min_length=1)
    tags: list[str] = Field(..., min_length=1)
    action: str = Field(default="add", pattern="^(add|remove)$")


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""

    success: bool
    affected: int
    message: str


# ============== List Params ==============


class ContactListParams(BaseModel):
    """Query parameters for contact list."""

    search: str | None = None
    company_id: int | None = None
    tags: list[str] | None = None
    owner_id: int | None = None
    source: str | None = None
    sort: str = "-created_at"
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class CompanyListParams(BaseModel):
    """Query parameters for company list."""

    search: str | None = None
    tags: list[str] | None = None
    owner_id: int | None = None
    industry: str | None = None
    sort: str = "-created_at"
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
