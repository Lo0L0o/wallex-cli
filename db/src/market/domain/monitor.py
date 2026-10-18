from typing import Protocol

from market.domain.market import MarketSnapshot, PricePoint
from market.domain.repositories import MarketRepository


class MonitorRepository(MarketRepository, Protocol):
    async def snapshot(self) -> MarketSnapshot: ...

    async def history(self, symbol: str, limit: int) -> list[PricePoint]: ...

    async def acquire_sync(self, now: float, min_age: int, retry_after: int) -> str | None: ...

    async def finish_sync(self, token: str, snapshot: MarketSnapshot) -> None: ...

    async def release_sync(self, token: str) -> None: ...


class MarketCache(Protocol):
    async def get(self) -> MarketSnapshot | None: ...

    async def set(self, snapshot: MarketSnapshot, ttl: int) -> None: ...

    async def close(self) -> None: ...


class MarketUnavailable(Exception):
    pass


class SyncInProgress(Exception):
    pass
