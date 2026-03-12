"""Module AI context model for storing extracted parameters from onboarding/setup."""

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ModuleContext(TimestampMixin, Base):
    """Stores extracted parameters from AI onboarding/setup dialogs per module."""

    __tablename__ = "module_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    module: Mapped[str] = mapped_column(String(50), nullable=False)

    # All extracted variables as JSON (dynamic key-value pairs)
    context_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Onboarding status
    onboarding_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    onboarding_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="module_contexts")

    __table_args__ = (
        UniqueConstraint("tenant_id", "module", name="uq_module_context_tenant_module"),
        Index("ix_module_context_tenant", "tenant_id"),
        Index("ix_module_context_module", "module"),
    )

    def __repr__(self) -> str:
        return f"<ModuleContext {self.tenant_id}:{self.module}>"

    def get_variable(self, key: str, default=None):
        """Get a single variable from context_data."""
        return self.context_data.get(key, default)

    def set_variable(self, key: str, value) -> None:
        """Set a single variable in context_data."""
        if self.context_data is None:
            self.context_data = {}
        self.context_data[key] = value

    def delete_variable(self, key: str) -> bool:
        """Delete a variable from context_data. Returns True if existed."""
        if self.context_data and key in self.context_data:
            del self.context_data[key]
            return True
        return False
