from decimal import Decimal

from market.domain.repositories import MarketRepository


class GetPrice:
    def __init__(self, repository: MarketRepository) -> None:
        self._repository = repository

    async def execute(self, symbol: str) -> Decimal | None:
        return await self._repository.get_price(symbol)