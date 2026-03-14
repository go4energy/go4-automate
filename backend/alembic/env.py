"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
import importlib
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.config import settings
from app.database import Base


def _import_model_modules() -> None:
    """Import all domain model modules without depending on manifest discovery.

    Alembic only needs tables in ``Base.metadata``. Importing ``__manifest__`` files
    pulls in avoidable module-level side effects and has caused brittle migration runs.
    For migrations we can scan ``app/*/models.py`` directly and import only those
    modules that actually define ORM models.
    """

    app_dir = Path(__file__).resolve().parent.parent / "app"
    skip_dirs = {"__pycache__", "utils", "routers", "models", "services"}

    for models_path in app_dir.glob("*/models.py"):
        module_name = models_path.parent.name
        if module_name.startswith("_") or module_name in skip_dirs:
            continue
        importlib.import_module(f"app.{module_name}.models")


_import_model_modules()

# Shared models (no __manifest__.py)
from app.models.activity_log import ActivityLog  # noqa: E402, F401
from app.models.chat_message import ChatMessage  # noqa: E402, F401
from app.models.conversation import Conversation  # noqa: E402, F401
from app.models.prompt import Prompt  # noqa: E402, F401
from app.models.tenant import Tenant  # noqa: E402, F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run migrations with a given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
