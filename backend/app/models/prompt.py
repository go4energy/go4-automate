"""Prompt registry model."""

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Prompt(TimestampMixin, Base):
    """Prompt template with versioning and LLM configuration."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="general"
    )

    # Module association (e.g., "linkedin", "emailmarketing", "global")
    module: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="global"
    )
    # Prompt type: "setup" (onboarding/config) or "productive" (system/n8n calls)
    prompt_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="productive"
    )
    # Is this a system prompt (from manifest) or user-created?
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    # For setup prompts: schema defining which variables to extract
    variables_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Template fields — placeholders use {{VARIABLE}} syntax
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # Variable definitions: [{name, type, required, default, description}]
    variables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Output configuration
    output_format: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="text"
    )
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # LLM configuration
    provider: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="anthropic"
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    temperature: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.7"
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="2048"
    )

    # Processing mode: "batch" (all findings at once) or "each" (one finding per call)
    processing_mode: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="batch"
    )

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    # Sort order for UI display
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Relationships
    tenant = relationship("Tenant", back_populates="prompts")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "slug", "version", name="uq_prompt_tenant_slug_version"
        ),
        Index("ix_prompt_tenant_slug", "tenant_id", "slug"),
        Index("ix_prompt_tenant_category", "tenant_id", "category"),
        Index("ix_prompt_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Prompt {self.slug} v{self.version}>"
