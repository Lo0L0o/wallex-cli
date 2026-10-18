import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from market.config import Settings
from market.infrastructure.persistence.database import sqlite_url
from market.infrastructure.persistence.models import Base


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    settings = Settings.from_environment()
    if settings.database_driver != "sqlite":
        raise ValueError("The web monitor migrations use SQLite; set DB_DRIVER=sqlite")
    engine = create_async_engine(sqlite_url(settings.sqlite_path))
    try:
        async with engine.begin() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("This migration inspects the existing database; run it online without --sql")
else:
    asyncio.run(online())
