import asyncio
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

import mysql.connector

from market.domain.market import Market


class MySQLMarketRepository:
    """Async contract over a blocking driver; each operation owns its connection."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def _connect(self):
        connection = mysql.connector.connect(**self._config)
        cursor = connection.cursor()
        try:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS market (
                    symbol VARCHAR(50) PRIMARY KEY,
                    price DECIMAL(20, 8) NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
                )"""
            )
            connection.commit()
        except Exception:
            connection.close()
            raise
        finally:
            cursor.close()
        return connection

    async def save_many(self, markets: Sequence[Market]) -> None:
        await asyncio.to_thread(self._save_many, markets)

    def _save_many(self, markets: Sequence[Market]) -> None:
        rows = [(market.symbol, market.price) for market in markets]
        with self._connect() as connection:
            cursor = connection.cursor()
            try:
                if rows:
                    cursor.executemany(
                        """INSERT INTO market (symbol, price) VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE price = VALUES(price)""",
                        rows,
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()

    async def list_all(self) -> list[Market]:
        return await asyncio.to_thread(
            self._query_markets, "SELECT symbol, price FROM market ORDER BY symbol"
        )

    async def search(self, query: str) -> list[Market]:
        return await asyncio.to_thread(
            self._query_markets,
            "SELECT symbol, price FROM market WHERE symbol LIKE %s ORDER BY symbol",
            (f"%{query}%",),
        )

    async def get_price(self, symbol: str) -> Decimal | None:
        return await asyncio.to_thread(self._get_price, symbol)

    def _get_price(self, symbol: str) -> Decimal | None:
        with self._connect() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT price FROM market WHERE symbol = %s", (symbol,))
                row = cursor.fetchone()
            finally:
                cursor.close()
        if row is None:
            return None
        if not isinstance(row, tuple) or len(row) != 1:
            raise ValueError("MySQL returned an unexpected price row")
        return Decimal(str(row[0]))

    def _query_markets(self, sql: str, params: tuple[str, ...] = ()) -> list[Market]:
        with self._connect() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            finally:
                cursor.close()
        markets = []
        for row in rows:
            if not isinstance(row, tuple) or len(row) != 2:
                raise ValueError("MySQL returned an unexpected market row")
            symbol, price = row
            if not isinstance(symbol, str):
                raise ValueError("MySQL returned a non-string market symbol")
            markets.append(Market(symbol, Decimal(str(price))))
        return markets
