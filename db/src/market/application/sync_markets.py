from market.domain.repositories import MarketRepository
from market.domain.services import MarketProvider


class SyncMarkets:
    def __init__(self, provider: MarketProvider, repository: MarketRepository) -> None:
        self._provider = provider
        self._repository = repository

    async def execute(self) -> int:
            markets = await self._provider.fetch_markets()
            await self._repository.save_many(markets)
            return len(markets)

