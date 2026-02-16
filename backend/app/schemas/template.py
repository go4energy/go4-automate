"""Template schemas."""

from pydantic import BaseModel


class TemplateListItem(BaseModel):
    """Schema for template list item."""

    category: str
    filename: str


class TemplateResponse(BaseModel):
    """Schema for template response."""

    category: str
    filename: str
    content: str


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""

    content: str
