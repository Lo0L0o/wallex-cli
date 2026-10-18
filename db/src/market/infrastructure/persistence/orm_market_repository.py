import time
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, update

from market.domain.market import Market, MarketSnapshot, PricePoint
from market.domain.monitor import SyncInProgress
from market.infrastructure.persistence.database import Database
from market.infrastructure.persistence.models import MarketRow, PriceRow, SyncRow


class OrmMarketRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _market(row: MarketRow) -> Market:
        return Market(row.symbol, Decimal(row.price), row.quote_asset, Decimal(row.quote_volume))

    async def list_all(self) -> list[Market]:
        async with self.database.sessions() as session:
            rows = await session.scalars(select(MarketRow).order_by(MarketRow.symbol))
            return [self._market(row) for row in rows]

    async def search(self, query: str) -> list[Market]:
        async with self.database.sessions() as session:
            rows = await session.scalars(
                select(MarketRow)
                .where(MarketRow.symbol.contains(query, autoescape=True))
                .order_by(MarketRow.symbol)
            )
            return [self._market(row) for row in rows]

    async def get_price(self, symbol: str) -> Decimal | None:
        async with self.database.sessions() as session:
            row = await session.get(MarketRow, symbol.upper())
            return Decimal(row.price) if row is not None else None

    async def snapshot(self) -> MarketSnapshot:
        async with self.database.sessions() as session:
            state = await session.get(SyncRow, 1)
            stamp = state.last_success if state else 0
            updated_at = datetime.fromtimestamp(stamp, timezone.utc) if stamp else None
            query = select(MarketRow).order_by(MarketRow.symbol)
            if updated_at is not None:
                query = query.where(MarketRow.updated_at == updated_at.isoformat())
            rows = await session.scalars(query)
            return MarketSnapshot([self._market(row) for row in rows], updated_at)

    async def history(self, symbol: str, limit: int = 100) -> list[PricePoint]:
        async with self.database.sessions() as session:
            rows = list(
                await session.scalars(
                    select(PriceRow)
                    .where(PriceRow.symbol == symbol)
                    .order_by(PriceRow.id.desc())
                    .limit(limit)
                )
            )
            return [
                PricePoint(Decimal(row.price), datetime.fromisoformat(row.recorded_at))
                for row in reversed(rows)
            ]

    async def acquire_sync(
        self, now: float, min_age: int = 60, retry_after: int = 15
    ) -> str | None:
        token = uuid4().hex
        async with self.database.sessions.begin() as session:
            result = await session.execute(
                update(SyncRow)
                .where(
                    SyncRow.id == 1,
                    SyncRow.lease_until <= now,
                    SyncRow.last_success <= now - min_age,
                    SyncRow.last_attempt <= now - retry_after,
                )
                .values(token=token, lease_until=now + 120, last_attempt=now)
            )
            return token if result.rowcount == 1 else None

    async def finish_sync(self, token: str, snapshot: MarketSnapshot) -> None:
        if snapshot.updated_at is None:
            raise ValueError("A new snapshot needs an update time")
        stamp = snapshot.updated_at.isoformat()
        async with self.database.sessions.begin() as session:
            # Claim the state row before writing prices. An expired owner cannot commit.
            result = await session.execute(
                update(SyncRow)
                .where(
                    SyncRow.id == 1,
                    SyncRow.token == token,
                    SyncRow.lease_until > time.time(),
                )
                .values(last_success=snapshot.updated_at.timestamp(), lease_until=0, token=None)
            )
            if result.rowcount != 1:
                raise SyncInProgress("The update lease expired; its result was discarded")
            existing = {row.symbol: row for row in await session.scalars(select(MarketRow))}
            for market in snapshot.markets:
                row = existing.get(market.symbol)
                if row is None:
                    row = MarketRow(symbol=market.symbol)
                    session.add(row)
                row.price = str(market.price)
                row.quote_asset = market.quote_asset
                row.quote_volume = str(market.quote_volume)
                row.updated_at = stamp
            await session.flush()
            session.add_all(
                [
                    PriceRow(symbol=m.symbol, price=str(m.price), recorded_at=stamp)
                    for m in snapshot.markets
                ]
            )

    async def release_sync(self, token: str) -> None:
        async with self.database.sessions.begin() as session:
            await session.execute(
                update(SyncRow)
                .where(SyncRow.id == 1, SyncRow.token == token)
                .values(token=None, lease_until=0)
            )

    async def save_many(self, markets) -> None:
        token = await self.acquire_sync(time.time(), min_age=0, retry_after=0)
        if token is None:
            raise SyncInProgress("Another market update is running")
        try:
            await self.finish_sync(token, MarketSnapshot(list(markets), datetime.now(timezone.utc)))
        finally:
            await self.release_sync(token)
