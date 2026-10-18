import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from market.domain.market import MarketSnapshot
from market.domain.monitor import (
    MarketCache,
    MarketUnavailable,
    MonitorRepository,
    SyncInProgress,
)
from market.domain.services import MarketProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnapshotResult:
    snapshot: MarketSnapshot
    source: str
    stale: bool


class MarketMonitor:
    def __init__(
        self,
        provider: MarketProvider,
        repository: MonitorRepository,
        cache: MarketCache,
        ttl: int = 60,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.cache = cache
        self.ttl = ttl
        self._lock = asyncio.Lock()

    def _fresh(self, snapshot: MarketSnapshot) -> bool:
        return (
            snapshot.updated_at is not None
            and 0 <= time.time() - snapshot.updated_at.timestamp() < self.ttl
        )

    async def _cache_snapshot(self, snapshot: MarketSnapshot) -> None:
        stamp = snapshot.updated_at
        if stamp is not None and self._fresh(snapshot):
            remaining = self.ttl - (time.time() - stamp.timestamp())
            await self.cache.set(snapshot, max(1, int(remaining)))

    async def _update(self, force: bool = False) -> MarketSnapshot | None:
        token = await self.repository.acquire_sync(
            time.time(),
            min_age=0 if force else self.ttl,
            retry_after=0 if force else 15,
        )
        if token is None:
            return None
        try:
            markets = await asyncio.wait_for(self.provider.fetch_markets(), timeout=20)
            if not markets:
                raise MarketUnavailable("Wallex returned no usable markets")
            symbols = [m.symbol for m in markets]
            if len(set(symbols)) != len(symbols):
                raise MarketUnavailable("Wallex returned duplicate market symbols")
            snapshot = MarketSnapshot(markets, datetime.now(timezone.utc))
            await self.repository.finish_sync(token, snapshot)
            await self._cache_snapshot(snapshot)
            return snapshot
        finally:
            await self.repository.release_sync(token)

    async def current(self) -> SnapshotResult:
        cached = await self.cache.get()
        if cached is not None and self._fresh(cached):
            return SnapshotResult(cached, "redis", False)
        async with self._lock:
            cached = await self.cache.get()
            if cached is not None and self._fresh(cached):
                return SnapshotResult(cached, "redis", False)
            saved = await self.repository.snapshot()
            if self._fresh(saved):
                await self._cache_snapshot(saved)
                return SnapshotResult(saved, "database", False)
            try:
                updated = await self._update()
                if updated is not None:
                    return SnapshotResult(updated, "wallex", False)
                saved = await self.repository.snapshot()
            except Exception:
                logger.exception("Market refresh failed; checking saved prices")
            if saved.markets:
                return SnapshotResult(saved, "database", not self._fresh(saved))
            raise MarketUnavailable(
                "No saved prices are available; the next request will retry shortly"
            )

    async def sync(self) -> int:
        async with self._lock:
            snapshot = await self._update(force=True)
            if snapshot is None:
                raise SyncInProgress("Another process is updating market prices")
            return len(snapshot.markets)

    async def scheduled_sync(self) -> None:
        async with self._lock:
            try:
                await self._update()
            except Exception:
                logger.exception("Scheduled market update failed")

    async def wait_idle(self) -> None:
        async with self._lock:
            pass
