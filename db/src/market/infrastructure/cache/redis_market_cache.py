import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from redis.asyncio import Redis
from redis.exceptions import RedisError

from market.domain.market import Market, MarketSnapshot

logger = logging.getLogger(__name__)


class RedisMarketCache:
    def __init__(self, url: str, key: str) -> None:
        self.client = Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        self.key = key

    async def get(self) -> MarketSnapshot | None:
        try:
            raw = await self.client.get(self.key)
            if raw is None:
                return None
            data = json.loads(raw)
            stamp = datetime.fromisoformat(data["updated_at"])
            if stamp.tzinfo is None:
                raise ValueError("Cached timestamps must include a timezone")
            return MarketSnapshot(
                [
                    Market(
                        m["symbol"],
                        Decimal(m["price"]),
                        m["quote_asset"],
                        Decimal(m["quote_volume"]),
                    )
                    for m in data["markets"]
                ],
                stamp,
            )
        except (
            RedisError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            InvalidOperation,
            AttributeError,
        ):
            logger.warning("Market cache read failed; using the database")
            return None

    async def set(self, snapshot: MarketSnapshot, ttl: int) -> None:
        if snapshot.updated_at is None:
            return
        data = {
            "updated_at": snapshot.updated_at.isoformat(),
            "markets": [
                {
                    "symbol": m.symbol,
                    "price": str(m.price),
                    "quote_asset": m.quote_asset,
                    "quote_volume": str(m.quote_volume),
                }
                for m in snapshot.markets
            ],
        }
        try:
            await self.client.set(self.key, json.dumps(data), ex=ttl)
        except (RedisError, OSError):
            logger.warning("Market cache write failed; prices remain saved in the database")

    async def close(self) -> None:
        await self.client.aclose()
