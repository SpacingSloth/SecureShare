
import sys
from logging.config import fileConfig

from sqlalchemy import pool

from alembic import context

config = context.config

fileConfig(config.config_file_name)

import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, APP_DIR)

from app.core.database import Base

target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = ""  
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"},
        compare_type=True, compare_server_default=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode using a sync engine built
    from the app's DATABASE_URL (converted from sqlite+aiosqlite to sqlite)."""
    from sqlalchemy import create_engine

    from app.core.database import DATABASE_URL
    sync_url = DATABASE_URL.replace("+aiosqlite", "")  
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():

    run_migrations_offline()
else:
    run_migrations_online()