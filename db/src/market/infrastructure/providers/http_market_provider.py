from decimal import Decimal, InvalidOperation

import httpx

from market.domain.market import Market


class HttpMarketProvider:
    def __init__(self, url: str, timeout: float = 10) -> None:
        self._url = url
        self._timeout = timeout
        self._session = httpx.AsyncClient()

    async def fetch_markets(self) -> list[Market]:
        response = await self._session.get(
            self._url,
            timeout=self._timeout
        )

        response.raise_for_status()
        payload = response.json()

        try:
            rows = payload["result"]["markets"]

        except (KeyError, TypeError) as error:
            raise ValueError(
                "Market API response is missing result.markets"
            ) from error

        markets: list[Market] = []

        for row in rows:
            price = row.get("price")

            if price in (None, ""):
                continue

            try:
                market = Market(
                    str(row["symbol"]).strip(),
                    Decimal(str(price))
                )

                markets.append(market)

            except (KeyError, TypeError, InvalidOperation) as error:
                raise ValueError(
                    "Market API returned an invalid market"
                ) from error

        return markets

    async def close(self) -> None:
        await self._session.aclose()