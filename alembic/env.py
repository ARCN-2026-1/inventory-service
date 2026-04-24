from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

resolve_alembic_database_url = __import__(
    "internal.infrastructure.config.settings",
    fromlist=["resolve_alembic_database_url"],
).resolve_alembic_database_url
Base = __import__(
    "internal.infrastructure.persistence.models",
    fromlist=["Base"],
).Base

config = context.config
resolved_database_url = resolve_alembic_database_url(
    config.get_main_option("sqlalchemy.url")
)

# configparser interpolation treats `%` specially. Runtime URLs can include
# percent-encoded credentials/params (e.g. `%23`), so we must escape `%` before
# setting the option through Alembic's config wrapper.
config.set_main_option(
    "sqlalchemy.url",
    resolved_database_url.replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
ALEMBIC_VERSION_TABLE = "inventory_alembic_version"


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        version_table=ALEMBIC_VERSION_TABLE,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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
            version_table=ALEMBIC_VERSION_TABLE,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
