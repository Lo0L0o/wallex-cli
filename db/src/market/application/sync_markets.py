from market.application.market_monitor import MarketMonitor
from market.domain.repositories import MarketRepository
from market.domain.services import MarketProvider


class SyncMarkets:
    def __init__(
        self,
        provider: MarketProvider,
        repository: MarketRepository,
        monitor: MarketMonitor | None = None,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._monitor = monitor

    async def execute(self) -> int:
        if self._monitor is not None:
            return await self._monitor.sync()
        markets = await self._provider.fetch_markets()
        await self._repository.save_many(markets)
        return len(markets)
