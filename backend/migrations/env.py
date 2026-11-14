import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# This comment on the import tells VS Code formatting tools (Ruff/isort/Flake8)
# NOT to delete this import on save, even though it appears "unused".
import app.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from DATABASE_URL env var if set.
# This allows both local dev (.env sourced in shell) and AWS ECS (task definition
# env vars) to inject the correct connection string without touching alembic.ini.
# Falls back to the value in alembic.ini when DATABASE_URL is not set.
_db_url = os.environ.get("DATABASE_URL")
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)

# Set the target metadata for SQLModel
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include non-public schemas (e.g. 'audit') so autogenerate
        # correctly detects audit.event instead of flagging it as missing.
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Include non-public schemas (e.g. 'audit') so autogenerate
            # correctly detects audit.event instead of flagging it as missing.
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
