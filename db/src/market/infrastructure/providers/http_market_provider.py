from decimal import Decimal

import httpx
from pydantic import BaseModel, Field, ValidationError

from market.domain.market import Market


class WallexMarket(BaseModel):
    symbol: str = Field(pattern=r"^[A-Z0-9]{1,50}$")
    price: Decimal = Field(ge=0, allow_inf_nan=False)
    quote_asset: str = Field(max_length=10)
    quote_volume: Decimal = Field(default=Decimal("0"), ge=0, allow_inf_nan=False)


class HttpMarketProvider:
    def __init__(self, url: str, timeout: float = 10) -> None:
        self._url = url
        self._timeout = timeout
        self._session = httpx.AsyncClient(headers={"Accept": "application/json"})

    async def fetch_markets(self) -> list[Market]:
        response = await self._session.get(self._url, timeout=self._timeout)
        response.raise_for_status()
        try:
            rows = response.json()["result"]["markets"]
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError("Wallex response is missing result.markets") from error
        if isinstance(rows, dict):
            rows = list(rows.values())
        if not isinstance(rows, list):
            raise ValueError("Wallex markets must be a list or an object")
        markets = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Wallex returned an invalid market row")
            stats = row.get("stats") or {}
            if not isinstance(stats, dict):
                raise ValueError("Wallex returned invalid market stats")
            price = row.get("price")
            if price is None:
                price = stats.get("lastPrice")
            if price in (None, ""):
                continue
            symbol = row.get("symbol")
            if not isinstance(symbol, str):
                raise ValueError("Wallex returned a market without a string symbol")
            symbol = symbol.strip().upper()
            quote = row.get("quote_asset") or row.get("quoteAsset")
            if quote is None:
                quote = next((q for q in ("USDT", "TMN") if symbol.endswith(q)), "")
            try:
                item = WallexMarket.model_validate(
                    {
                        "symbol": symbol,
                        "price": price,
                        "quote_asset": quote,
                        "quote_volume": row.get("quote_volume_24h", stats.get("24h_quoteVolume"))
                        or "0",
                    }
                )
            except ValidationError as error:
                raise ValueError(f"Wallex returned invalid values for {symbol}") from error
            markets.append(Market(item.symbol, item.price, item.quote_asset, item.quote_volume))
        return markets

    async def close(self) -> None:
        await self._session.aclose()
