"""Setup wizard schemas."""

from pydantic import BaseModel


class ModuleStatus(BaseModel):
    """Status of a single setup module."""

    label: str
    configured: bool
    details: str


class SetupStatusResponse(BaseModel):
    """Overall setup progress."""

    modules: dict[str, ModuleStatus]
