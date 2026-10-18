from hashlib import sha256
from pathlib import Path

from market.application.get_price import GetPrice
from market.application.list_markets import ListMarkets
from market.application.market_monitor import MarketMonitor
from market.application.search_markets import SearchMarkets
from market.application.sync_markets import SyncMarkets
from market.config import Settings
from market.domain.repositories import MarketRepository
from market.infrastructure.cache.redis_market_cache import RedisMarketCache
from market.infrastructure.persistence.database import Database
from market.infrastructure.persistence.orm_market_repository import OrmMarketRepository
from market.infrastructure.providers.http_market_provider import HttpMarketProvider


class ApplicationContainer:
    def __init__(self, settings: Settings) -> None:
        self.database: Database | None = None
        self.cache: RedisMarketCache | None = None
        self.monitor: MarketMonitor | None = None
        repository: OrmMarketRepository | None = None
        self.market_repository: MarketRepository
        if settings.database_driver == "mysql":
            from market.infrastructure.persistence.mysql_market_repository import (
                MySQLMarketRepository,
            )

            self.market_repository = MySQLMarketRepository(settings.mysql)
        else:
            self.database = Database(settings.sqlite_path)
            repository = OrmMarketRepository(self.database)
            self.market_repository = repository
            namespace = sha256(str(Path(settings.sqlite_path).resolve()).encode()).hexdigest()[:16]
            self.cache = RedisMarketCache(settings.redis_url, f"market:{namespace}:snapshot:v1")
        self.market_provider = HttpMarketProvider(settings.market_api_url)
        if repository is not None and self.cache is not None:
            self.monitor = MarketMonitor(
                self.market_provider, repository, self.cache, settings.cache_ttl
            )
        self.sync_markets = SyncMarkets(self.market_provider, self.market_repository, self.monitor)
        self.list_markets = ListMarkets(self.market_repository)
        self.search_markets = SearchMarkets(self.market_repository)
        self.get_price = GetPrice(self.market_repository)

    async def close(self) -> None:
        try:
            await self.market_provider.close()
        finally:
            try:
                if self.cache is not None:
                    await self.cache.close()
            finally:
                if self.database is not None:
                    await self.database.close()
