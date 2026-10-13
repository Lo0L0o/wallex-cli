from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from market.domain.market import Market


class MarketRepository(Protocol):
    """Persistence contract; database adapters supply backend-specific behavior."""

    async def save_many(self, markets: Sequence[Market]) -> None: ...

    async def list_all(self) -> list[Market]: ...

    async def search(self, query: str) -> list[Market]: ...

    async def get_price(self, symbol: str) -> Decimal | None: ...