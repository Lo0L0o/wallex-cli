from market.domain.market import Market
from market.domain.repositories import MarketRepository


class SearchMarkets:
    def __init__(self, repository: MarketRepository) -> None:
        self._repository = repository

    async def execute(self, query: str) -> list[Market]:
        return await self._repository.search(query)