"""Composition root: choose infrastructure implementations and connect layers."""

from market.application.list_markets import ListMarkets
from market.application.sync_markets import SyncMarkets
from market.config import Settings
from market.domain.repositories import MarketRepository
from market.infrastructure.persistence.sqlite_market_repository import SQLiteMarketRepository
from market.infrastructure.providers.http_market_provider import HttpMarketProvider
from market.application.search_markets import SearchMarkets
from market.application.get_price import GetPrice


class ApplicationContainer:
    def __init__(self, settings: Settings) -> None:
        self.market_provider = HttpMarketProvider(settings.market_api_url)
        self.market_repository: MarketRepository = self._create_repository(settings)
        self.sync_markets = SyncMarkets(self.market_provider, self.market_repository)
        self.list_markets = ListMarkets(self.market_repository)
        self.search_markets = SearchMarkets(self.market_repository)
        self.get_price = GetPrice (self.market_repository)

    @staticmethod
    def _create_repository(settings: Settings) -> MarketRepository:
        if settings.database_driver == "mysql":
            from market.infrastructure.persistence.mysql_market_repository import MySQLMarketRepository

            return MySQLMarketRepository(settings.mysql)
        return SQLiteMarketRepository(settings.sqlite_path)

    async def close(self) -> None:
        await self.market_provider.close()
