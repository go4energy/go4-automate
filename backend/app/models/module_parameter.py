"""Module parameter model for dynamic onboarding variables."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModuleParameter(Base):
    """
    Defines a parameter/variable for a module's onboarding process.

    The Setup Assistant uses these parameters to:
    1. Know which questions to ask
    2. Extract values from the conversation
    3. Store the collected values
    """

    __tablename__ = "module_parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)

    # Parameter definition
    variable: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Type: "string", "array", "boolean", "number"
    var_type: Mapped[str] = mapped_column(String(20), server_default="string")
    required: Mapped[bool] = mapped_column(Boolean, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ModuleParameter {self.module}.{self.variable}>"
