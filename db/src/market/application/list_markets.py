from market.domain.market import Market
from market.domain.repositories import MarketRepository


class ListMarkets:
    def __init__(self, repository: MarketRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Market]:
        return await self._repository.list_all()
