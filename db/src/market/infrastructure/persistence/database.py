from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def sqlite_url(path: str) -> URL:
    return URL.create("sqlite+aiosqlite", database=str(Path(path).resolve()))


class Database:
    def __init__(self, path: str) -> None:
        self.engine = create_async_engine(sqlite_url(path), connect_args={"timeout": 30})
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

        @event.listens_for(self.engine.sync_engine, "connect")
        def configure_connection(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async def close(self) -> None:
        await self.engine.dispose()
