from typing import Protocol

from market.domain.market import Market


class MarketProvider(Protocol):
    """Contract for any external source of market data."""

    async def fetch_markets(self) -> list[Market]: ...

