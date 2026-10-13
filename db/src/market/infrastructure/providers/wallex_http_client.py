import json
import os
from decimal import Decimal
from urllib.request import Request, urlopen

from market.domain.market import Market


def fetch_markets(request_id):
    url = os.getenv("MARKET_API_URL", "https://api.wallex.ir/hector/web/v1/markets")
    request = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "wallex-learning-project",
        "X-Request-ID": request_id,
    })
    with urlopen(request, timeout=10) as response:
        data = json.load(response)

    rows = data["result"]["markets"]
    if isinstance(rows, dict):
        rows = rows.values()

    markets = []
    for row in rows:
        price = row.get("price")
        if price is None:
            price = row.get("stats", {}).get("lastPrice")
        if price in (None, ""):
            continue
        markets.append(Market(str(row["symbol"]), Decimal(str(price))))
    return markets
