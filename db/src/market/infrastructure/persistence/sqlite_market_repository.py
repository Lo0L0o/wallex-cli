from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from decimal import Decimal

import aiosqlite

from market.domain.market import Market


class SQLiteMarketRepository:
    """Async SQLite storage."""

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        async with aiosqlite.connect(self._database_path) as connection:
            await connection.execute(
                """CREATE TABLE IF NOT EXISTS market (
                    symbol TEXT PRIMARY KEY,
                    price TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )

            await connection.commit()

            try:
                yield connection
                await connection.commit()

            except Exception:
                await connection.rollback()
                raise

    async def save_many(self, markets: Sequence[Market]) -> None:
        async with self._connect() as connection:
            await connection.executemany(
                """INSERT INTO market (symbol, price) VALUES (?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    price = excluded.price,
                    updated_at = CURRENT_TIMESTAMP""",
                [
                    (market.symbol, str(market.price))
                    for market in markets
                ],
            )

    async def list_all(self) -> list[Market]:
        async with self._connect() as connection:
            async with connection.execute(
                "SELECT symbol, price FROM market ORDER BY symbol"
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            Market(symbol, Decimal(price))
            for symbol, price in rows
        ]

    async def search(self, query: str) -> list[Market]:
        async with self._connect() as connection:
            async with connection.execute(
                "SELECT symbol, price FROM market WHERE symbol LIKE ? ORDER BY symbol",
                (f"%{query}%",),
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            Market(symbol, Decimal(price))
            for symbol, price in rows
        ]

    async def get_price(self, symbol: str) -> Decimal | None:
        async with self._connect() as connection:
            async with connection.execute(
                "SELECT price FROM market WHERE symbol = ?",
                (symbol,),
            ) as cursor:
                row = await cursor.fetchone()

        return Decimal(row[0]) if row else None