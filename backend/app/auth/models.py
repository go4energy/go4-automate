"""Auth models — User, Group, and user_groups association."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

# Many-to-many association table
user_groups = Table(
    "user_groups",
    Base.metadata,
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "group_id",
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(TimestampMixin, Base):
    """Platform user for the admin interface."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    permissions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    groups = relationship("Group", secondary=user_groups, back_populates="users")

    # Ownership relationships
    owned_contacts = relationship("Contact", back_populates="owner", lazy="selectin")
    owned_companies = relationship("Company", back_populates="owner", lazy="selectin")
    owned_deals = relationship("CrmDeal", back_populates="owner", lazy="selectin")

    # CRM relationships
    crm_activities = relationship("CrmActivity", back_populates="user", lazy="selectin")
    assigned_tasks = relationship(
        "CrmTask",
        foreign_keys="CrmTask.assigned_to",
        back_populates="assignee",
        lazy="selectin",
    )
    created_tasks = relationship(
        "CrmTask",
        foreign_keys="CrmTask.created_by",
        back_populates="creator",
        lazy="selectin",
    )

    # Funnels relationships
    owned_funnels = relationship("Funnel", back_populates="owner", lazy="selectin")
    funnel_prospects = relationship(
        "FunnelProspect", back_populates="owner", lazy="selectin"
    )
    funnel_activities_created = relationship(
        "FunnelActivity", back_populates="user", lazy="selectin"
    )

    # Surveys relationships
    surveys = relationship("Survey", back_populates="owner", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("ix_users_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email!r}>"


class Group(TimestampMixin, Base):
    """Permission group that users can be assigned to."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    users = relationship("User", secondary=user_groups, back_populates="groups")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_groups_tenant_name"),
        Index("ix_groups_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<Group {self.name!r}>"
