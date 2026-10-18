from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Market:
    symbol: str
    price: Decimal
    quote_asset: str = ""
    quote_volume: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("Market symbol cannot be empty")
        if not self.price.is_finite() or self.price < 0:
            raise ValueError("Market price must be a finite, non-negative number")
        if not self.quote_volume.is_finite() or self.quote_volume < 0:
            raise ValueError("Market volume must be finite and non-negative")


@dataclass(frozen=True)
class PricePoint:
    price: Decimal
    recorded_at: datetime


@dataclass(frozen=True)
class MarketSnapshot:
    markets: list[Market]
    updated_at: datetime | None
